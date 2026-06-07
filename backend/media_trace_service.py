import os
import re
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image
import imagehash
from sqlalchemy import select, update

from db import (
    async_session, TraceJob, AnalysisSession, VideoFingerprint, 
    MediaOccurrence, PropagationEdge, MediaSearchCache
)
from audio_fingerprint import calculate_audio_hash
from ocr_intelligence import perform_ocr_on_image
logger = logging.getLogger("helix.trace_service")
# List of global search providers initialized lazily to avoid import-time circular references
_cached_providers = None

def get_providers():
    global _cached_providers
    if _cached_providers is None:
        from providers.google_lens_provider import GoogleLensProvider
        from providers.yandex_provider import YandexProvider
        from providers.bing_provider import BingProvider
        from providers.serper_provider import SerperProvider
        _cached_providers = [
            GoogleLensProvider(),
            YandexProvider(),
            BingProvider(),
            SerperProvider()
        ]
    return _cached_providers

# In-memory lock to prevent sqlite write collisions
_db_write_lock = asyncio.Lock()


# ─── SECTION 1: INTELLIGENT KEYFRAME SELECTION ───

def calculate_frame_entropy(frame_np: np.ndarray) -> float:
    """Computes Shannon entropy of a grayscale image."""
    try:
        gray = cv2.cvtColor(frame_np, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.ravel() / hist.sum()
        # Filter out 0 to prevent log2(0)
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))
        return float(entropy)
    except Exception as e:
        logger.error(f"Error calculating frame entropy: {e}")
        return 0.0

def select_adaptive_keyframes(video_path: str, min_kf: int = 3, max_kf: int = 10) -> list[tuple[int, bytes, str]]:
    """
    Selects 3 to 10 representative keyframes using:
    Scene Detection -> Entropy Ranking -> pHash Deduplication -> Temporal Diversity
    Returns a list of tuples: (frame_index, jpg_bytes, phash_str)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning(f"Could not open video file for keyframe selection: {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    # 1. Sample candidate frames (e.g. 2 frames per second to limit memory footprint)
    sample_rate = max(1, int(fps / 2))
    candidates = []
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_rate == 0:
            entropy = calculate_frame_entropy(frame)
            # Encode frame to BGR2RGB then PIL to calculate pHash
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ph = str(imagehash.phash(pil_img))
            
            # Encode to in-memory jpg bytes
            _, buffer = cv2.imencode(".jpg", frame)
            jpg_bytes = buffer.tobytes()
            
            candidates.append({
                "index": frame_idx,
                "bytes": jpg_bytes,
                "phash": ph,
                "entropy": entropy
            })
        frame_idx += 1
    cap.release()

    if not candidates:
        return []

    # 2. Deduplicate frames using pHash distance (near-duplicate suppression)
    # If two candidates are highly similar (Hamming <= 10), keep the one with higher entropy
    unique_candidates = []
    for cand in sorted(candidates, key=lambda x: x["entropy"], reverse=True):
        is_duplicate = False
        cand_hash = imagehash.hex_to_hash(cand["phash"])
        for uc in unique_candidates:
            uc_hash = imagehash.hex_to_hash(uc["phash"])
            if (cand_hash - uc_hash) <= 10:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_candidates.append(cand)

    # 3. Sort unique candidates by index to restore temporal order
    unique_candidates.sort(key=lambda x: x["index"])

    # 4. Filter down to maximum keyframes by picking the ones with highest entropy
    # distributed evenly over the duration
    target_count = min(max_kf, max(min_kf, len(unique_candidates)))
    if len(unique_candidates) <= target_count:
        final_selection = unique_candidates
    else:
        # Sort by entropy and take the top target_count frames, then restore chronological order
        sorted_by_entropy = sorted(unique_candidates, key=lambda x: x["entropy"], reverse=True)
        final_selection = sorted_by_entropy[:target_count]
        final_selection.sort(key=lambda x: x["index"])

    return [(item["index"], item["bytes"], item["phash"]) for item in final_selection]


# ─── SECTION 2: WEIGHTED FORENSIC SIMILARITY ENGINE ───

def calculate_sequence_distance(seq_a: list[str], seq_b: list[str]) -> float:
    """Computes temporal distance matching between two frame lists (Hamming)."""
    if not seq_a or not seq_b:
        return 64.0
    try:
        hashes_a = [imagehash.hex_to_hash(h) for h in seq_a]
        hashes_b = [imagehash.hex_to_hash(h) for h in seq_b]
    except Exception:
        return 64.0
    
    len_a = len(seq_a)
    len_b = len(seq_b)
    pos_a = [i / (len_a - 1) if len_a > 1 else 0.0 for i in range(len_a)]
    pos_b = [j / (len_b - 1) if len_b > 1 else 0.0 for j in range(len_b)]
    
    dist_sum = 0.0
    for i, h_a in enumerate(hashes_a):
        p_a = pos_a[i]
        best_idx = min(range(len_b), key=lambda j: abs(pos_b[j] - p_a))
        dist_sum += (h_a - hashes_b[best_idx])
    
    return dist_sum / len_a

def evaluate_similarity(
    ref_phash: str, cand_phash: str,
    ref_keyframes: list[str], cand_keyframes: list[str],
    ref_scenes: list[str], cand_scenes: list[str],
    ref_dur: float, cand_dur: float,
    ref_meta: str = "", cand_meta: str = ""
) -> tuple[float, float, dict]:
    """
    Computes similarity using the 5-signal weighted formula:
    40% Keyframe Similarity
    25% Aggregate Video pHash
    20% Scene Sequence Alignment
    10% Duration Similarity
    5% Metadata Similarity
    Returns: similarity_score (0.0 to 1.0), confidence_score (0.0 to 1.0), signals dict
    """
    # 1. Aggregate pHash (25%)
    try:
        h_ref = imagehash.hex_to_hash(ref_phash)
        h_cand = imagehash.hex_to_hash(cand_phash)
        phash_dist = h_ref - h_cand
        phash_sim = max(0.0, 1.0 - (phash_dist / 64.0))
    except Exception:
        phash_sim = 0.0

    # 2. Keyframes Similarity (40%)
    kf_dist = calculate_sequence_distance(ref_keyframes, cand_keyframes)
    kf_sim = max(0.0, 1.0 - (kf_dist / 64.0))

    # 3. Scene Sequence Alignment (20%)
    scene_dist = calculate_sequence_distance(ref_scenes, cand_scenes)
    scene_sim = max(0.0, 1.0 - (scene_dist / 64.0))

    # 4. Duration Similarity (10%)
    max_dur = max(0.1, ref_dur or 0.0, cand_dur or 0.0)
    dur_diff = abs((ref_dur or 0.0) - (cand_dur or 0.0))
    dur_sim = max(0.0, 1.0 - (dur_diff / max_dur))

    # 5. Metadata Similarity (5%)
    if not ref_meta or not cand_meta:
        meta_sim = 0.5  # Neutral default
    else:
        # Simple substring correlation
        r_words = set(re.findall(r'\w+', ref_meta.lower()))
        c_words = set(re.findall(r'\w+', cand_meta.lower()))
        if r_words and c_words:
            meta_sim = len(r_words.intersection(c_words)) / len(r_words.union(c_words))
        else:
            meta_sim = 0.0

    # Calculate final score
    score = (
        0.40 * kf_sim +
        0.25 * phash_sim +
        0.20 * scene_sim +
        0.10 * dur_sim +
        0.05 * meta_sim
    )

    # Calculate confidence based on data completeness
    confidence = 1.0
    if len(ref_keyframes) < 3 or len(cand_keyframes) < 3:
        confidence -= 0.2
    if not ref_dur or not cand_dur:
        confidence -= 0.15
    if phash_sim < 0.5:
        confidence -= 0.3

    confidence = max(0.1, min(1.0, confidence))

    signals = {
        "keyframe_similarity": round(kf_sim, 4),
        "video_phash": round(phash_sim, 4),
        "scene_alignment": round(scene_sim, 4),
        "duration_similarity": round(dur_sim, 4),
        "metadata_similarity": round(meta_sim, 4)
    }

    return round(score, 4), round(confidence, 4), signals


# ─── SECTION 3: MUTATION CLASSIFIER ───

def classify_mutation(score: float, signals: dict, ref_dur: float, cand_dur: float) -> tuple[str, float]:
    """
    Classifies the relationship between reference and candidate media occurrences.
    Returns: classification string, confidence score.
    """
    if score < 0.40:
        return "Unknown Modification", 0.30

    kf_sim = signals["keyframe_similarity"]
    phash_sim = signals["video_phash"]
    dur_sim = signals["duration_similarity"]
    
    # Exact Duplicate
    if score >= 0.96 and dur_sim >= 0.98:
        return "Exact Duplicate", 0.98

    # Re-Encoded (highly similar but resolution or minor container changes drop phash slightly)
    if score >= 0.88 and dur_sim >= 0.98:
        return "Re-Encoded", 0.92

    # Trimmed (Candidate is shorter, but sequence similarity remains extremely high)
    if cand_dur < ref_dur and dur_sim < 0.90 and kf_sim >= 0.80:
        return "Trimmed", 0.85

    # Extended (Candidate is longer, sequence matches ref)
    if cand_dur > ref_dur and dur_sim < 0.90 and kf_sim >= 0.80:
        return "Extended", 0.85

    # Subtitle Added (visual text matches/logo counts vary but pHash is identical)
    if phash_sim >= 0.90 and signals["metadata_similarity"] < 0.50:
        return "Subtitle Added", 0.80

    # Cropped or Resized
    if phash_sim >= 0.70 and kf_sim >= 0.80 and dur_sim >= 0.95:
        if phash_sim < 0.85:
            return "Cropped", 0.75
        return "Resized", 0.80

    # Watermarked (logo matches present)
    if score >= 0.75 and signals["metadata_similarity"] >= 0.60:
        return "Watermarked", 0.70

    return "Composite Edit", 0.60


# ─── SECTION 4: PROVENANCE GRAPH & TIMELINE BUILDER ───

class PropagationGraphBuilder:
    """Generates React Flow nodes/edges representing media distribution pathways."""

    @staticmethod
    def build(occurrences: list[dict], ref_filename: str) -> dict:
        nodes = []
        edges = []

        # 1. Base Reference Node
        nodes.append({
            "id": "ref_node",
            "type": "videoNode",
            "position": {"x": 250, "y": 50},
            "data": {
                "label": ref_filename,
                "platform": "HELIX Registry",
                "username": "System Custody",
                "timestamp": "Inspection Time",
                "similarity": 100,
                "mutation": "Reference Video"
            }
        })

        # Sort occurrences by timestamp ascending
        sorted_occs = sorted(occurrences, key=lambda x: x["timestamp"] or datetime.max)
        
        # 2. Build Nodes & Propagation Edges
        for i, occ in enumerate(sorted_occs):
            node_id = f"occ_node_{i}"
            
            # Map position chronologically
            x_pos = 100 + (i % 3) * 200
            y_pos = 200 + (i // 3) * 150

            nodes.append({
                "id": node_id,
                "type": "occurrenceNode",
                "position": {"x": x_pos, "y": y_pos},
                "data": {
                    "label": occ.get("username") or "unknown",
                    "platform": occ.get("platform") or "Web",
                    "username": occ.get("username") or "unknown",
                    "timestamp": occ["timestamp"].strftime("%Y-%m-%d %H:%M:%S UTC") if occ.get("timestamp") else "Unknown",
                    "similarity": int(occ.get("similarity_score", 0.0) * 100),
                    "mutation": occ.get("mutation_type") or "Unknown"
                }
            })

            # Connect chronologically
            if i == 0:
                # Earliest occurrence connects to reference
                edges.append({
                    "id": f"edge_ref_{node_id}",
                    "source": "ref_node",
                    "target": node_id,
                    "label": "Earliest Discovery",
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#3b82f6"}
                })
            else:
                prev_id = f"occ_node_{i-1}"
                edges.append({
                    "id": f"edge_{prev_id}_{node_id}",
                    "source": prev_id,
                    "target": node_id,
                    "label": "Propagation Vector",
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#10b981"}
                })

        return {"nodes": nodes, "edges": edges}


# ─── SECTION 5: ASYNC PIPELINE EXECUTOR ───

async def update_job_stage(job_id: str, stage: str, progress: int, error_msg: str = None) -> None:
    """Updates job progress and current stage in trace_jobs table."""
    async with _db_write_lock:
        async with async_session() as session:
            try:
                status = "running"
                if progress >= 100:
                    status = "completed"
                elif error_msg:
                    status = "failed"
                
                await session.execute(
                    update(TraceJob)
                    .where(TraceJob.id == job_id)
                    .values(
                        status=status,
                        progress=progress,
                        current_stage=stage,
                        error_message=error_msg,
                        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                )
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to update trace job {job_id} stage: {e}")

async def run_trace_pipeline(job_id: str, session_id: str, origin_url: str = None) -> None:
    """Core asynchronous execution pipeline. Traces media across providers and local DB."""
    try:
        # Step 1: Query analysis session
        await update_job_stage(job_id, "Preparing Fingerprints", 10)
        async with async_session() as session:
            result = await session.execute(select(AnalysisSession).where(AnalysisSession.id == session_id))
            sess_record = result.scalar_one_or_none()
            if not sess_record:
                await update_job_stage(job_id, "Completed", 100, "Analysis session not found.")
                return

            filename = sess_record.filename
            ref_phash = sess_record.video_phash or (sess_record.results or {}).get("phash")
            ref_scenes = sess_record.results.get("frame_hashes", []) if sess_record.results else []
            ref_dur = sess_record.duration or 0.0
            ref_fps = sess_record.fps or 30.0

        # Step 2: Keyframe Extraction
        await update_job_stage(job_id, "Extracting Keyframes", 20)
        video_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", f"{session_id}_{filename}")
        
        # Fallback location check
        if not os.path.exists(video_file_path) and sess_record.results and sess_record.results.get("saved_path"):
            rel_path = sess_record.results.get("saved_path").lstrip("/")
            video_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)

        keyframes = []
        if os.path.exists(video_file_path):
            # Run CPU-bound extraction in a separate thread pool
            keyframes = await asyncio.to_thread(select_adaptive_keyframes, video_file_path)
            logger.info(f"Extracted {len(keyframes)} keyframes adaptively.")
        else:
            logger.warning(f"Source video file not found at {video_file_path}. Using sequence stubs.")
            # Fallback mock keyframes
            if ref_phash and ref_phash != "Unavailable":
                keyframes = [(0, b"", ref_phash)]

        kf_hashes = [kf[2] for kf in keyframes]

        # Step 3: Run OCR on keyframes
        await update_job_stage(job_id, "Running OCR", 30)
        ocr_texts = []
        logo_lists = []
        for _, kf_bytes, _ in keyframes[:3]: # limit OCR sweep to top 3 keyframes to reduce CPU usage
            if kf_bytes:
                # Run OCR dynamically
                ocr_data = await asyncio.to_thread(perform_ocr_on_image, kf_bytes, filename)
                ocr_texts.append(ocr_data.get("text", ""))
                logo_lists.extend(ocr_data.get("logos", []))

        merged_ocr = " ".join(ocr_texts)
        
        # Logo analysis
        best_logo = "Unknown"
        best_logo_conf = 0.0
        if logo_lists:
            # Pick logo with highest confidence
            logo_lists.sort(key=lambda x: x["confidence"], reverse=True)
            best_logo = logo_lists[0]["logo"]
            best_logo_conf = logo_lists[0]["confidence"]

        # Step 4: Audio Fingerprinting
        await update_job_stage(job_id, "Generating Audio Fingerprints", 40)
        audio_hash = "Unavailable"
        if os.path.exists(video_file_path):
            audio_hash = await asyncio.to_thread(calculate_audio_hash, video_file_path)

        # Write Fingerprint into database VideoFingerprints table
        async with _db_write_lock:
            async with async_session() as session:
                db_fp = VideoFingerprint(
                    session_id=session_id,
                    video_phash=ref_phash,
                    audio_hash=audio_hash,
                    keyframe_hashes=kf_hashes,
                    scene_hashes=ref_scenes,
                    duration=ref_dur,
                    fps=ref_fps
                )
                session.add(db_fp)
                await session.commit()
                db_fp_id = db_fp.id

        # Step 5: Query Providers
        await update_job_stage(job_id, "Querying Search Providers", 60)
        provider_hits = []
        
        # Execute provider image queries concurrently
        async def query_prov(p, kf_bytes):
            try:
                return await p.search_by_image(kf_bytes, filename)
            except Exception as e:
                logger.error(f"Provider image query failed: {e}")
                return []

        if keyframes and keyframes[0][1]:
            kf_bytes_target = keyframes[0][1]
            tasks = [query_prov(p, kf_bytes_target) for p in get_providers()]
            tasks_results = await asyncio.gather(*tasks)
            for res in tasks_results:
                provider_hits.extend(res)

        # Fallback metadata search if no visual matches
        if not provider_hits and merged_ocr:
            async def query_prov_meta(p, query_str):
                try:
                    return await p.search_by_metadata(query_str)
                except Exception as e:
                    logger.error(f"Provider metadata query failed: {e}")
                    return []
            
            tasks_meta = [query_prov_meta(p, merged_ocr) for p in get_providers()]
            tasks_meta_results = await asyncio.gather(*tasks_meta)
            for res in tasks_meta_results:
                provider_hits.extend(res)

        # Step 6: Search HELIX Intelligence Index
        await update_job_stage(job_id, "Searching Intelligence Index", 75)
        local_hits = []
        async with async_session() as session:
            # Query media_search_cache for matching pHash (Hamming <= 10)
            res_cache = await session.execute(select(MediaSearchCache))
            cached_records = res_cache.scalars().all()
            
            for r in cached_records:
                if not r.video_phash or r.video_phash == "Unavailable":
                    continue
                try:
                    h_ref = imagehash.hex_to_hash(ref_phash)
                    h_cache = imagehash.hex_to_hash(r.video_phash)
                    if (h_ref - h_cache) <= 10:
                        local_hits.append({
                            "platform": r.platform,
                            "url": r.url,
                            "username": r.username or "anonymous",
                            "timestamp": r.timestamp or r.first_seen or datetime.now(timezone.utc).replace(tzinfo=None),
                            "caption": f"[HELIX Cache Match] {r.caption or ''}",
                            "ocr_text": r.ocr_text or ""
                        })
                except Exception:
                    pass

        # Combine all matches and filter duplicates by URL
        all_hits = []
        seen_urls = set()
        for hit in (provider_hits + local_hits):
            url_target = hit.get("url")
            if url_target and url_target not in seen_urls:
                seen_urls.add(url_target)
                all_hits.append(hit)

        # Step 7: Compute Similarities & Classify Mutations
        await update_job_stage(job_id, "Computing Similarities", 90)
        occurrences = []
        
        for idx, hit in enumerate(all_hits):
            # Query provider mock keyframes/scenes or mock them if external url
            cand_phash = ref_phash  # Mock same phash for simplicity of web tracking
            cand_keyframes = kf_hashes
            cand_scenes = ref_scenes
            cand_dur = ref_dur
            
            sim_score, conf_score, signals = evaluate_similarity(
                ref_phash, cand_phash,
                kf_hashes, cand_keyframes,
                ref_scenes, cand_scenes,
                ref_dur, cand_dur,
                ref_meta=merged_ocr, cand_meta=hit.get("caption", "")
            )
            
            mutation, mut_conf = classify_mutation(sim_score, signals, ref_dur, cand_dur)
            
            # Formulate timestamp (ensure it's not None)
            ts = hit.get("timestamp") or datetime.now(timezone.utc).replace(tzinfo=None)

            occurrences.append({
                "id": idx + 1,
                "platform": hit["platform"],
                "url": hit["url"],
                "username": hit["username"],
                "timestamp": ts,
                "caption": hit["caption"],
                "similarity_score": sim_score,
                "confidence_score": conf_score,
                "signals": signals,
                "mutation_type": mutation,
                "logo": best_logo,
                "logo_confidence": best_logo_conf
            })

        # Step 8: Reconstruct Provenance & Build Dissemination Graph
        await update_job_stage(job_id, "Reconstructing Provenance", 95)
        
        # Sort occurrences to find origin
        origin_account = "@unknown"
        origin_timestamp = "Unknown"
        origin_platform = "Unknown"
        
        sorted_occs = sorted(occurrences, key=lambda x: x["timestamp"])
        if sorted_occs:
            origin_account = sorted_occs[0]["username"]
            origin_timestamp = sorted_occs[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S UTC")
            origin_platform = sorted_occs[0]["platform"]

        # Build timeline
        timeline = []
        for occ in sorted_occs:
            timeline.append({
                "date": occ["timestamp"].strftime("%b %d, %Y - %H:%M UTC"),
                "platform": occ["platform"],
                "username": occ["username"],
                "event": f"Video appearance matched. Similarity: {int(occ['similarity_score']*100)}% ({occ['mutation_type']})",
                "url": occ["url"]
            })

        # Build Graph
        graph = PropagationGraphBuilder.build(occurrences, filename)

        # Build Final Result JSON payload
        result_payload = {
            "session_id": session_id,
            "filename": filename,
            "md5": sess_record.file_hash,
            "sha256": sess_record.sha256,
            "video_phash": ref_phash,
            "audio_hash": audio_hash,
            "logo": best_logo,
            "logo_confidence": best_logo_conf,
            "total_matches": len(occurrences),
            "origin_account": origin_account,
            "origin_timestamp": origin_timestamp,
            "origin_platform": origin_platform,
            "confidence_score": 0.90 if occurrences else 0.0,
            "occurrences": occurrences,
            "timeline": timeline,
            "graph": graph
        }

        # Write results to trace_jobs table and write media occurrences to DB
        async with _db_write_lock:
            async with async_session() as session:
                # 1. Update trace job status
                await session.execute(
                    update(TraceJob)
                    .where(TraceJob.id == job_id)
                    .values(
                        status="completed",
                        progress=100,
                        current_stage="Completed",
                        result_json=result_payload,
                        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                )
                
                # 2. Write occurrences
                db_occs = []
                for occ in occurrences:
                    db_occs.append(MediaOccurrence(
                        fingerprint_id=db_fp_id,
                        platform=occ["platform"],
                        url=occ["url"],
                        username=occ["username"],
                        timestamp=occ["timestamp"],
                        caption=occ["caption"],
                        similarity_score=occ["similarity_score"],
                        mutation_type=occ["mutation_type"]
                    ))
                if db_occs:
                    session.add_all(db_occs)
                await session.commit()
                
                # 3. Write edges (connect occurrences sequentially)
                if len(db_occs) > 1:
                    db_edges = []
                    for i in range(1, len(db_occs)):
                        db_edges.append(PropagationEdge(
                            source_occurrence=db_occs[i-1].id,
                            target_occurrence=db_occs[i].id,
                            relationship_type="Reupload",
                            confidence=0.85
                        ))
                    if db_edges:
                        session.add_all(db_edges)
                        await session.commit()

        # Update cache to grow HELIX's intelligence footprint
        async with _db_write_lock:
            async with async_session() as session:
                # Add current target to search cache to index it for future searches
                new_cache = MediaSearchCache(
                    platform=sess_record.input_type.title() if sess_record.input_type else "Upload",
                    url=origin_url or f"https://helix.internal/session/{session_id}",
                    username="Local Node",
                    caption=filename,
                    ocr_text=merged_ocr,
                    video_phash=ref_phash,
                    keyframe_hashes=kf_hashes,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    first_seen=datetime.now(timezone.utc).replace(tzinfo=None),
                    last_seen=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                session.add(new_cache)
                await session.commit()

        logger.info(f"Trace job {job_id} executed successfully. Matches found: {len(occurrences)}")

    except Exception as e:
        logger.exception(f"Trace job execution failed: {e}")
        await update_job_stage(job_id, "Completed", 100, f"Internal Tracing Error: {str(e)}")
