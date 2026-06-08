import os
import re
import json
import io
import math
import time
import secrets
import logging
import asyncio
import base64
import httpx
from datetime import datetime, timezone
import cv2
import numpy as np
from PIL import Image
import imagehash
from sqlalchemy import select, insert

# Import existing database session and models
from db import async_session, SerpApiCache, LandmarkIntelligenceSession, LandmarkDetection, OCRDetection, L12ClusterResult, AuditLog
from evidence import Evidence

logger = logging.getLogger("helix.visual_location_intelligence")

# ──────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────
MAX_KEYFRAMES_PER_VIDEO = int(os.getenv("MAX_KEYFRAMES_PER_VIDEO", "10"))
MAX_VISION_API_REQUESTS_PER_SESSION = int(os.getenv("MAX_VISION_API_REQUESTS_PER_SESSION", "5"))
MAX_SERPAPI_REQUESTS_PER_SESSION = int(os.getenv("MAX_SERPAPI_REQUESTS_PER_SESSION", "5"))
MAX_GEOCODING_REQUESTS_PER_SESSION = int(os.getenv("MAX_GEOCODING_REQUESTS_PER_SESSION", "20"))

PIPELINE_VERSION = "1.2.0"
PROMPT_VERSION = "1.0.0"
FORCE_SERP_REFRESH = os.getenv("FORCE_SERP_REFRESH", "False").lower() in ("true", "1", "yes")

DBSCAN_EPSILON_KM = float(os.getenv("DBSCAN_EPSILON_KM", "50.0"))
DBSCAN_MIN_SAMPLES = int(os.getenv("DBSCAN_MIN_SAMPLES", "2"))

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", "")

# Moondream confidence word to float mapping
MOONDREAM_CONF_MAP = {
    "clearly": 0.90,
    "likely": 0.75,
    "possibly": 0.50,
    "default": 0.60
}

# Signal Weights for Composite Scoring
SIGNAL_WEIGHTS = {
    "vision_api_native": 1.0,
    "vision_api_geocoded": 0.85,
    "serpapi_knowledge_graph": 0.80,
    "moondream_landmark": 0.75,
    "serpapi_visual_matches": 0.60,
    "ocr_geocoded": 0.50,
    "moondream_context": 0.30
}

def calculate_image_quality(gray_img: np.ndarray, entropy: float) -> float:
    if gray_img is None:
        return 0.0
    # Sharpness: Laplacian variance
    sharpness = float(cv2.Laplacian(gray_img, cv2.CV_64F).var())
    normalized_sharpness = min(1.0, sharpness / 500.0)
    
    # Contrast: standard deviation of pixel intensities
    contrast = float(np.std(gray_img))
    normalized_contrast = min(1.0, contrast / 127.0)
    
    # Entropy normalization (max entropy for 256 bins is 8.0)
    normalized_entropy = min(1.0, entropy / 8.0)
    
    # Quality score
    quality_score = normalized_sharpness * 0.4 + normalized_contrast * 0.3 + normalized_entropy * 0.3
    return float(quality_score)

def names_agree(name1: str, name2: str) -> bool:
    if not name1 or not name2:
        return False
    # Lowercase and strip punctuation
    n1 = re.sub(r'[^\w\s]', '', name1.lower()).strip()
    n2 = re.sub(r'[^\w\s]', '', name2.lower()).strip()
    
    if n1 == n2:
        return True
        
    # Tokenize and extract keywords (excluding common small words)
    stop_words = {"hotel", "palace", "the", "of", "and", "in", "at", "on", "by", "a", "an", "temple", "tower", "bridge", "station", "airport", "museum", "park", "monument", "landmark"}
    tokens1 = [w for w in n1.split() if w not in stop_words and len(w) > 2]
    tokens2 = [w for w in n2.split() if w not in stop_words and len(w) > 2]
    
    t1 = set(tokens1)
    t2 = set(tokens2)
    
    # 1. Token intersection
    intersection = t1 & t2
    if intersection:
        if len(intersection) >= min(len(t1), len(t2), 2) or (len(t1) == 1 or len(t2) == 1):
            return True
            
    # 2. Substring matching
    if len(n1) > 4 and len(n2) > 4:
        if n1 in n2 or n2 in n1:
            return True
            
    # 3. Token Jaccard similarity fallback
    union = t1 | t2
    if union:
        jaccard = len(intersection) / len(union)
        if jaccard >= 0.4:
            return True
            
    return False

def is_allowed_location_entity(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    
    text_lower = text.lower().strip()
    
    # 1. Reject URLs and domains
    if re.search(r"https?://|www\.|ftp://", text_lower):
        return False
    if re.search(r"\b[a-z0-9-]+\.(com|org|net|io|edu|gov|co|info|biz|me|us|uk|in|de|fr|jp|tv|xyz|html|php|js|py|sh|pl|json)\b", text_lower):
        return False
        
    # 2. Reject software, programming, and technical terms/phrases
    rejected_phrases = {
        "help center", "documentation", "terms of service", "privacy policy", "terms of use", "cookie policy"
    }
    for phrase in rejected_phrases:
        if phrase in text_lower:
            return False

    rejected_tech = {
        "javascript", "python", "html", "css", "java", "ruby", "rust", "golang", "c++",
        "programming", "software", "app", "application", "database", "sql", "api", "url",
        "domain", "website", "webpage", "developer", "development", "faq",
        "support", "login", "signup", "register", "download", "install", "update",
        "github", "gitlab", "bitbucket", "npm", "pip", "docker", "kubernetes", "code",
        "function", "class", "null", "undefined", "true", "false", "script"
    }
    for word in text_lower.split():
        w_clean = re.sub(r'[^\w\.-]', '', word)
        if w_clean in rejected_tech:
            return False
            
    # 3. Reject generic description nouns, adjectives, and phrases
    rejected_generic_patterns = [
        r"\b(large|small|tall|beautiful|ornate|modern|historic|old|new|ornated|gorgeous|magnificent|scenic)\s+(building|structure|tower|house|bridge|palace|temple|church|monument|landmark|street|city|scenery|image|photo|picture)\b",
        r"\b(nature|scenery|landscape|outdoors|indoors|interior|exterior|room|sky|cloud|water|river|sea|ocean|beach|lake|mountain|hill|forest|tree|grass|flower|animal|bird|cat|dog|car|bus|train|plane|person|man|woman|child|people|crowd)\b",
        r"\b(avian visitors|lively atmosphere|lively street|busy market|crowded area|scenic view|beautiful day|great view)\b",
        r"\b(no landmarks?|none|n/a|unknown|not available|null|undefined)\b",
        r"\b(the image features|this is a picture of|photo of|photograph of|shot of|view of|picture of)\b"
    ]
    for pattern in rejected_generic_patterns:
        if re.search(pattern, text_lower):
            return False
            
    return True

def extract_landmark_candidates(raw_text: str) -> dict:
    """Fallback extractor using regex and NER to extract candidates from unstructured text."""
    res = {
        "landmark_candidates": [],
        "building_candidates": [],
        "city_candidates": [],
        "country_candidates": [],
        "confidence_reasoning": "Extracted via fallback parser",
        "l9_narrative": raw_text
    }
    if not raw_text:
        return res

    # 1. Regex-based candidate extraction: find sequences of capitalized words
    pattern = r'\b[A-Z][a-zA-Z0-9]*(?:\s+(?:of|in|at|the|and|de|for|by)\s+[A-Z][a-zA-Z0-9]*|\s+[A-Z][a-zA-Z0-9]*)*\b'
    regex_candidates = re.findall(pattern, raw_text)
    
    # 2. NER-based candidate extraction (using HELIX spaCy NER via _ner_engine)
    ner_entities = []
    try:
        from backend import _ner_engine
        if _ner_engine:
            ner_entities = _ner_engine.extract_ner_entities(raw_text)
    except Exception as e:
        logger.warning(f"Could not use spaCy NER for fallback extraction: {e}")

    # Combine candidates from both extractors
    all_raw_candidates = list(set(regex_candidates + ner_entities))
    
    # Common country list for classification
    common_countries = {
        "india", "united states", "usa", "united kingdom", "uk", "canada", "australia", "germany", "france", 
        "spain", "italy", "japan", "china", "brazil", "mexico", "russia", "egypt", "turkey", "singapore", 
        "switzerland", "netherlands", "sweden", "norway", "belgium", "austria", "greece", "thailand", 
        "vietnam", "malaysia", "indonesia", "philippines", "united arab emirates", "uae", "saudi arabia"
    }

    def clean_entity(e: str) -> str:
        return e.strip().strip(",.()\"'-;")

    for cand in all_raw_candidates:
        cand_clean = clean_entity(cand)
        if not is_allowed_location_entity(cand_clean):
            continue
            
        cand_lower = cand_clean.lower()
        is_building = any(kw in cand_lower for kw in ["hotel", "palace", "building", "house", "tower", "bridge", "temple", "church", "cathedral", "castle", "mausoleum", "monument", "station", "airport", "hall", "plaza", "square"])
        
        if cand_lower in common_countries:
            if cand_clean not in res["country_candidates"]:
                res["country_candidates"].append(cand_clean)
        elif is_building:
            if cand_clean not in res["building_candidates"]:
                res["building_candidates"].append(cand_clean)
        else:
            words_count = len(cand_clean.split())
            if words_count <= 2:
                if cand_clean not in res["city_candidates"]:
                    res["city_candidates"].append(cand_clean)
            else:
                if cand_clean not in res["landmark_candidates"]:
                    res["landmark_candidates"].append(cand_clean)
                    
    # Deduplicate lists
    for k in ["landmark_candidates", "building_candidates", "city_candidates", "country_candidates"]:
        res[k] = list(dict.fromkeys(res[k]))
        
    return res

def parse_moondream_json(text_resp: str, run_l9_geoloc: bool = False) -> dict:
    cleaned = text_resp.strip()
    
    def make_schema_dict(d: dict) -> dict:
        res = {
            "landmark_candidates": [],
            "building_candidates": [],
            "city_candidates": [],
            "country_candidates": [],
            "confidence_reasoning": "",
            "l9_narrative": ""
        }
        if not isinstance(d, dict):
            return res
            
        for k in ["landmark_candidates", "building_candidates", "city_candidates", "country_candidates"]:
            val = d.get(k, [])
            if isinstance(val, list):
                res[k] = [str(x).strip() for x in val if x]
            elif isinstance(val, str):
                res[k] = [val.strip()]
                
        res["confidence_reasoning"] = str(d.get("confidence_reasoning", "")).strip()
        if "l9_narrative" in d or run_l9_geoloc:
            res["l9_narrative"] = str(d.get("l9_narrative", "")).strip()
            
        return res

    # 1. Try direct JSON parsing
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return make_schema_dict(data)
    except Exception:
        pass

    # 2. Extract JSON block from markdown
    try:
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if json_block_match:
            data = json.loads(json_block_match.group(1).strip())
            if isinstance(data, dict):
                return make_schema_dict(data)
    except Exception:
        pass

    # 3. Attempt repair parsing (soft repair)
    try:
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx+1]
            json_str = re.sub(r',\s*\}', '}', json_str)
            json_str = re.sub(r',\s*\]', ']', json_str)
            data = json.loads(json_str)
            if isinstance(data, dict):
                return make_schema_dict(data)
    except Exception:
        pass

    # 4. Fallback extraction if JSON parsing fails
    try:
        fallback_data = extract_landmark_candidates(text_resp)
        if any(fallback_data[k] for k in ["landmark_candidates", "building_candidates", "city_candidates", "country_candidates"]):
            logger.warning(f"Moondream JSON parsing failed. Fell back to regex/NER extraction for raw text: '{text_resp}'")
            return make_schema_dict(fallback_data)
    except Exception as e:
        logger.error(f"Fallback extraction failed: {e}")

    logger.warning(f"Moondream response could not be parsed into required schema. Raw text: '{text_resp}'")
    return {
        "status": "invalid_vlm_response",
        "raw_text": text_resp
    }

# ──────────────────────────────────────────────────────────────────────
# GEOGRAPHIC HELPERS
# ──────────────────────────────────────────────────────────────────────
def haversine_distance(coord1, coord2) -> float:
    """Computes the great-circle distance between two points in kilometers."""
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371.0  # Earth's radius in kilometers
    return c * r

def dbscan_haversine(coordinates: list, eps_km: float, min_samples: int) -> list[int]:
    """
    DBSCAN clustering algorithm utilizing haversine distance.
    coordinates: list of tuples (lat, lng, idx, confidence)
    Returns: list of cluster labels (-1 for noise)
    """
    n = len(coordinates)
    labels = [-2] * n  # -2 means unvisited
    
    def get_neighbors(i):
        neighbors = []
        for j in range(n):
            if i == j:
                continue
            dist = haversine_distance(coordinates[i][:2], coordinates[j][:2])
            if dist <= eps_km:
                neighbors.append(j)
        return neighbors

    cluster_id = 0
    for i in range(n):
        if labels[i] != -2:
            continue
        
        neighbors = get_neighbors(i)
        if len(neighbors) + 1 < min_samples:
            labels[i] = -1  # Mark as noise
        else:
            labels[i] = cluster_id
            queue = list(neighbors)
            for j in queue:
                if labels[j] == -1:
                    labels[j] = cluster_id
                elif labels[j] == -2:
                    labels[j] = cluster_id
                    j_neighbors = get_neighbors(j)
                    if len(j_neighbors) + 1 >= min_samples:
                        for k in j_neighbors:
                            if k not in queue:
                                queue.append(k)
            cluster_id += 1
            
    return labels

# ──────────────────────────────────────────────────────────────────────
# L12 SERVICE ENGINE
# ──────────────────────────────────────────────────────────────────────
class VisualLocationIntelligenceService:
    def __init__(self, request_id_context_var=None):
        self.request_id_var = request_id_context_var
        # In-memory OpenCage geocoding cache to deduplicate API calls
        self.geocode_cache = {}
        self.geocode_calls_count = 0

    async def log_audit_event(self, action: str, details: str, db=None):
        """Helper to write audit logs using Helix schema."""
        req_id = self.request_id_var.get() if self.request_id_var else None
        try:
            if db:
                db.add(AuditLog(
                    action=action,
                    details=details,
                    request_id=req_id
                ))
                await db.commit()
            else:
                async with async_session() as session:
                    session.add(AuditLog(
                        action=action,
                        details=details,
                        request_id=req_id
                    ))
                    await session.commit()
        except Exception as e:
            logger.error(f"Audit log writing failed: {e}")

    async def geocode_text(self, text: str) -> tuple[float | None, float | None, dict]:
        """Geocodes a text string using Helix's existing OpenCage client wrapper."""
        if not text:
            return None, None, {}
        
        cleaned = text.strip()
        if cleaned in self.geocode_cache:
            return self.geocode_cache[cleaned]

        if self.geocode_calls_count >= MAX_GEOCODING_REQUESTS_PER_SESSION:
            logger.warning(f"Geocoding budget exceeded. Skipping query: '{cleaned}'")
            return None, None, {}

        self.geocode_calls_count += 1
        
        # We dynamically import _resolver from backend to avoid circular dependencies
        try:
            from backend import _resolver
            res = await _resolver.resolve_entity(cleaned)
            if res and res.get("country"):
                lat = res.get("lat")
                lng = res.get("lng")
                # Parse coordinates to float
                if lat is not None and lng is not None:
                    coords = (float(lat), float(lng), res)
                    self.geocode_cache[cleaned] = coords
                    await self.log_audit_event("geocode_success", f"Resolved text: {cleaned[:50]} -> {res.get('country')}")
                    await self.log_audit_event("opencage_geocode", f"{coords[0]},{coords[1]}")
                    return coords[0], coords[1], res
            await self.log_audit_event("geocode_failed", f"Failed to geocode text: {cleaned[:50]}")
        except Exception as e:
            logger.error(f"OpenCage geocoding failed for '{cleaned}': {e}")
            await self.log_audit_event("geocode_failed", f"Failed to geocode text: {cleaned[:50]} (error: {str(e)})")

        self.geocode_cache[cleaned] = (None, None, {})
        return None, None, {}

    async def extract_scene_keyframes(self, video_path: str) -> list[tuple[int, bytes, str, float]]:
        """
        Uses standard Helix scene boundaries detection to extract stable keyframes.
        Deduplicates them using Hamming distance of pHash.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning(f"Could not open video file: {video_path}")
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        # Determine 0%, 25%, 50%, 75%, 100% indices
        must_extract_indices = set()
        if total_frames > 0:
            for p in [0.0, 0.25, 0.50, 0.75, 1.0]:
                must_extract_indices.add(min(total_frames - 1, int(total_frames * p)))

        # 1. Sample frames (2 frames per second) + percentage frames
        sample_rate = max(1, int(fps / 2))
        candidates = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_rate == 0 or frame_idx in must_extract_indices:
                # Compute entropy
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
                hist = hist / (hist.sum() or 1.0)
                hist = hist[hist > 0]
                entropy = -np.sum(hist * np.log2(hist))
                
                # Calculate quality score
                quality_score = calculate_image_quality(gray, entropy)
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                ph = str(imagehash.phash(pil_img))
                _, buffer = cv2.imencode(".jpg", frame)
                
                candidates.append({
                    "index": frame_idx,
                    "bytes": buffer.tobytes(),
                    "phash": ph,
                    "entropy": float(entropy),
                    "variance": float(np.var(gray)),
                    "quality_score": quality_score,
                    "is_percentage_frame": frame_idx in must_extract_indices
                })
                await self.log_audit_event("frame_extracted", f"Extracted frame ID {frame_idx} (quality_score={quality_score:.2f})")
            frame_idx += 1
        cap.release()

        if not candidates:
            return []

        # 2. Extract scene boundaries
        distances = []
        for i in range(1, len(candidates)):
            h1 = imagehash.hex_to_hash(candidates[i-1]["phash"])
            h2 = imagehash.hex_to_hash(candidates[i]["phash"])
            distances.append(h1 - h2)
            
        if distances:
            avg_dist = sum(distances) / len(distances)
            threshold = max(10.0, avg_dist * 1.5)
        else:
            threshold = 10.0

        # We grab the most visually stable frame (highest entropy) in each scene interval
        scene_boundaries = [0]
        for i, dist in enumerate(distances):
            if dist > threshold:
                scene_boundaries.append(candidates[i+1]["index"])
        scene_boundaries.append(total_frames)

        scene_keyframes = []
        # For each scene, find candidate with highest entropy and add it
        for idx_sb in range(len(scene_boundaries) - 1):
            start = scene_boundaries[idx_sb]
            end = scene_boundaries[idx_sb+1]
            scene_candidates = [c for c in candidates if start <= c["index"] < end]
            if scene_candidates:
                best_cand = max(scene_candidates, key=lambda x: x["entropy"])
                scene_keyframes.append(best_cand)

        # Also ensure percentage frames are added
        percentage_frames = [c for c in candidates if c["is_percentage_frame"]]
        for pf in percentage_frames:
            if not any(sk["index"] == pf["index"] for sk in scene_keyframes):
                scene_keyframes.append(pf)

        # Sort chronologically
        scene_keyframes.sort(key=lambda x: x["index"])

        # 3. Deduplicate keyframes: keep highest quality score when Hamming distance is <= 5
        accepted_keyframes = []
        for cand in scene_keyframes:
            cand_hash = imagehash.hex_to_hash(cand["phash"])
            duplicate_idx = -1
            for idx, ak in enumerate(accepted_keyframes):
                ak_hash = imagehash.hex_to_hash(ak["phash"])
                dist = cand_hash - ak_hash
                if dist <= 5:
                    duplicate_idx = idx
                    break
            
            if duplicate_idx == -1:
                accepted_keyframes.append(cand)
            else:
                existing = accepted_keyframes[duplicate_idx]
                if cand["quality_score"] > existing["quality_score"]:
                    await self.log_audit_event(
                        "frame_rejected", 
                        f"Frame ID {existing['index']} replaced by higher quality duplicate Frame ID {cand['index']} (quality {cand['quality_score']:.2f} > {existing['quality_score']:.2f})"
                    )
                    accepted_keyframes[duplicate_idx] = cand
                else:
                    await self.log_audit_event(
                        "frame_rejected",
                        f"Frame ID {cand['index']} discarded as duplicate of Frame ID {existing['index']} (quality {cand['quality_score']:.2f} <= {existing['quality_score']:.2f})"
                    )

        # Log selection of keyframes
        for ak in accepted_keyframes:
            await self.log_audit_event("frame_selected", f"Selected frame ID {ak['index']} for location intelligence pipeline (quality={ak['quality_score']:.2f})")

        return [(item["index"], item["bytes"], item["phash"], item["quality_score"]) for item in accepted_keyframes]

    async def prioritize_keyframes(self, keyframes: list, session_id: str, run_l9_geoloc_idx: int = -1) -> list:
        """
        Ranks and budgets keyframes to max_keyframes_per_video limit.
        Prioritizes: Moondream landmarks, OCR text, visual uniqueness, scene variance.
        """
        if len(keyframes) <= MAX_KEYFRAMES_PER_VIDEO:
            return keyframes

        scored_frames = []
        # Pre-assess using local models
        for idx, frame_data in enumerate(keyframes):
            frame_index = frame_data[0]
            jpg_bytes = frame_data[1]
            phash_str = frame_data[2]
            quality_score = frame_data[3] if len(frame_data) > 3 else 0.5
            
            score = 0.0
            
            # 1. Scene variance (normalized)
            gray = cv2.imdecode(np.frombuffer(jpg_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
            variance = float(np.var(gray)) if gray is not None else 0.0
            score += min(1.0, variance / 5000.0) * 0.1 # Weight 10%

            # 2. Local OCR text check
            has_ocr = False
            try:
                from backend import _ocr_manager
                ocr_res = _ocr_manager.run_ocr(jpg_bytes, f"f_{frame_index}.jpg")
                if ocr_res.get("status") == "success" and ocr_res.get("text"):
                    has_ocr = True
            except Exception:
                pass
            if has_ocr:
                score += 0.3 # Weight 30%

            # 3. Moondream local landmark signal check
            has_moondream_landmark = False
            try:
                # Retrieve local Moondream assessment
                b64 = base64.b64encode(jpg_bytes).decode("utf-8")
                # Avoid merging L9 calls here; just check L12 signal
                md_res = await self.query_moondream_local(b64, run_l9_geoloc=False)
                if md_res and md_res.get("landmark_candidates"):
                    has_moondream_landmark = True
            except Exception:
                pass
            if has_moondream_landmark:
                score += 0.4 # Weight 40%

            # 4. Visual uniqueness: average Hamming distance to all other keyframes
            avg_dist = 0.0
            c_hash = imagehash.hex_to_hash(phash_str)
            for other_data in keyframes:
                other_ph = other_data[2]
                if other_ph != phash_str:
                    avg_dist += (c_hash - imagehash.hex_to_hash(other_ph))
            if len(keyframes) > 1:
                avg_dist = avg_dist / (len(keyframes) - 1)
            score += (avg_dist / 64.0) * 0.2 # Weight 20%

            # Include quality score directly in the priority formula
            score += quality_score * 0.1

            scored_frames.append({
                "data": frame_data,
                "score": score
            })

        # Sort and take top MAX_KEYFRAMES_PER_VIDEO
        scored_frames.sort(key=lambda x: x["score"], reverse=True)
        selected = scored_frames[:MAX_KEYFRAMES_PER_VIDEO]
        
        # Log skipped keyframes
        for skipped in scored_frames[MAX_KEYFRAMES_PER_VIDEO:]:
            sf_idx = skipped["data"][0]
            await self.log_audit_event("frame_rejected", f"Frame ID {sf_idx} skipped due to budget limits")

        # Restore original chronological ordering
        selected.sort(key=lambda x: x["data"][0])
        return [x["data"] for x in selected]

    async def query_moondream_local(self, base64_image: str, run_l9_geoloc: bool = False) -> dict:
        """
        Queries the local Moondream vision model on LM Studio.
        If run_l9_geoloc=True, merges L9 visual description and L12 landmarks in a single query.
        """
        from backend import client, MODEL_VISION, LM_STUDIO_URL
        if not client:
            return {
                "landmark_candidates": [],
                "building_candidates": [],
                "city_candidates": [],
                "country_candidates": [],
                "confidence_reasoning": "",
                "l9_narrative": ""
            }

        if run_l9_geoloc:
            prompt = (
                "Return ONLY valid JSON.\n\n"
                "Do NOT describe the image.\n\n"
                "Do NOT write prose.\n\n"
                "Do NOT explain.\n\n"
                "Output must be parseable by json.loads().\n\n"
                "{\n"
                '  "landmark_candidates": [],\n'
                '  "building_candidates": [],\n'
                '  "city_candidates": [],\n'
                '  "country_candidates": [],\n'
                '  "confidence_reasoning": "",\n'
                '  "l9_narrative": "Detailed forensic narrative structured with a \'Suspected Location\' and \'Key Indicators\'"\n'
                "}"
            )
        else:
            prompt = (
                "Return ONLY valid JSON.\n\n"
                "Do NOT describe the image.\n\n"
                "Do NOT write prose.\n\n"
                "Do NOT explain.\n\n"
                "Output must be parseable by json.loads().\n\n"
                "{\n"
                '  "landmark_candidates": [],\n'
                '  "building_candidates": [],\n'
                '  "city_candidates": [],\n'
                '  "country_candidates": [],\n'
                '  "confidence_reasoning": ""\n'
                "}"
            )

        logger.warning(
            f"MOONDREAM PROMPT SENT:\n{prompt}"
        )

        try:
            # We call LM Studio API (no response_format={"type": "json_object"} to avoid failures on models without json mode)
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=MODEL_VISION,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.2
            )
            text_resp = response.choices[0].message.content
            
            # Parse responses using our soft JSON parsing fallback chain
            parsed = parse_moondream_json(text_resp, run_l9_geoloc=run_l9_geoloc)
            
            # Retry if parsed returns invalid_vlm_response
            if not parsed or parsed.get("status") == "invalid_vlm_response":
                logger.warning("Moondream response invalid, retrying with correction prompt...")
                retry_prompt = f"""
Your previous response was invalid.

Return ONLY JSON.

Previous response:

{text_resp}
"""
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=MODEL_VISION,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                            ]
                        },
                        {
                            "role": "assistant",
                            "content": text_resp
                        },
                        {
                            "role": "user",
                            "content": retry_prompt
                        }
                    ],
                    max_tokens=500,
                    temperature=0.2
                )
                text_resp = response.choices[0].message.content
                parsed = parse_moondream_json(text_resp, run_l9_geoloc=run_l9_geoloc)

            parsed["raw_text"] = text_resp
            return parsed

        except Exception as e:
            logger.error(f"LM Studio Moondream client call failed: {e}")
            return {"landmarks": [], "context": "", "l9_narrative": "", "raw_text": ""}

    async def query_google_vision(self, base64_image: str) -> dict:
        """
        Stub method replacing paid Google Cloud Vision API. Always returns empty lists/strings.
        """
        return {"landmarks": [], "text": "", "labels": []}

    async def query_serpapi_google_lens(self, token: str, p_hash: str, ignore_cache: bool = False) -> dict:
        """
        Queries SerpApi Google Lens endpoint with a cached lookup check.
        """
        # 1. Check pHash Cache first
        if not ignore_cache and not FORCE_SERP_REFRESH:
            async with async_session() as session:
                stmt = select(SerpApiCache).where(SerpApiCache.phash == p_hash)
                cached_res = await session.execute(stmt)
                cached_record = cached_res.scalar_one_or_none()
                if cached_record:
                    record_pipeline_ver = getattr(cached_record, "pipeline_version", None)
                    record_prompt_ver = getattr(cached_record, "prompt_version", None)
                    if record_pipeline_ver == PIPELINE_VERSION and record_prompt_ver == PROMPT_VERSION:
                        logger.info(f"SerpApi cache hit for pHash {p_hash}!")
                        await self.log_audit_event("serpapi_cache_hit", f"Cache hit for pHash: {p_hash}")
                        return cached_record.response_json
                    else:
                        logger.info(f"SerpApi cache hit for pHash {p_hash} invalidated due to version mismatch: "
                                    f"Record({record_pipeline_ver}, {record_prompt_ver}) vs Current({PIPELINE_VERSION}, {PROMPT_VERSION})")
                        await session.delete(cached_record)
                        await session.commit()

        if not SERPAPI_API_KEY:
            logger.warning("SERPAPI_API_KEY environment variable not set. Skipping Tier 2.")
            return {"knowledge_graph": [], "visual_matches": []}

        # Expose tokenized public URL
        ext_url = os.getenv("EXTERNAL_BASE_URL", "http://127.0.0.1:8000")
        temp_img_url = f"{ext_url}/api/frames/temp/{token}"

        serp_url = "https://serpapi.com/search"
        params = {
            "engine": "google_lens",
            "url": temp_img_url,
            "api_key": SERPAPI_API_KEY
        }

        try:
            await self.log_audit_event("serpapi_query", f"Querying SerpApi for image: {temp_img_url[:60]}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(serp_url, params=params)
                if resp.status_code != 200:
                    logger.error(f"SerpApi Google Lens call failed: HTTP {resp.status_code} - {resp.text}")
                    return {"knowledge_graph": [], "visual_matches": []}

                resp_data = resp.json()
                
                # Normalize result format
                kg = resp_data.get("knowledge_graph", [])
                vm = resp_data.get("visual_matches", [])
                
                result = {
                    "knowledge_graph": kg,
                    "visual_matches": vm
                }

                # Store response in cache
                async with async_session() as write_sess:
                    write_sess.add(SerpApiCache(
                        phash=p_hash,
                        response_json=result,
                        pipeline_version=PIPELINE_VERSION,
                        prompt_version=PROMPT_VERSION
                    ))
                    await write_sess.commit()

                return result

        except Exception as e:
            logger.error(f"SerpApi Google Lens execution failed: {e}")
            return {"knowledge_graph": [], "visual_matches": []}

    async def execute_l12_pipeline(self, file_bytes: bytes, filename: str, is_video: bool, session_id: str, db=None, ignore_cache: bool = False) -> dict:
        """
        Orchestrates the multi-tier visual geolocation and landmark intelligence flow.
        """
        await self.log_audit_event("l12_pipeline_started", f"Session ID: {session_id}, media={filename}, is_video={is_video}", db=db)
        
        # Write files temporarily for processing
        from backend import UPLOADS_DIR
        temp_filename = f"{session_id}_{filename}"
        video_path = os.path.join(UPLOADS_DIR, temp_filename)
        
        if not os.path.exists(video_path):
            with open(video_path, "wb") as f:
                f.write(file_bytes)

        # 1. Extract and Deduplicate keyframes
        keyframes = []
        if is_video:
            keyframes = await self.extract_scene_keyframes(video_path)
            await self.log_audit_event("l12_pipeline_started", f"Extracted {len(keyframes)} scene keyframes", db=db)
        else:
            # Create a single frame entry for images
            img_hash = str(imagehash.phash(Image.open(io.BytesIO(file_bytes))))
            keyframes = [(0, file_bytes, img_hash, 0.90)]

        # 2. Prioritize keyframes based on budget limits
        budget_keyframes = await self.prioritize_keyframes(keyframes, session_id)
        
        # Determine L9 middle frame index to merge prompt if required
        middle_idx = len(keyframes) // 2 if keyframes else -1
        middle_frame_index = keyframes[middle_idx][0] if middle_idx != -1 else -1

        # Pipeline results lists
        final_candidates = []
        detected_landmarks = []
        ocr_signals = []
        visual_search_matches = []
        supporting_evidence = []
        
        stats = {
            "total_frames_extracted": len(keyframes),
            "frames_after_deduplication": len(keyframes), # matches deduped count
            "frames_tier1_resolved": 0,
            "frames_tier2_resolved": 0,
            "frames_unresolved": 0
        }

        # Keep track of temporary tokens generated for clean up
        from backend import temp_tokens

        # Process frames concurrently
        async def process_frame(frame_data):
            frame_id = frame_data[0]
            frame_bytes = frame_data[1]
            p_hash = frame_data[2]
            quality_score = frame_data[3] if len(frame_data) > 3 else 0.5
            
            frame_label = f"frame_{frame_id}"
            
            # Save frame to disk permanently for timeline & evidence preservation
            frame_filename = f"{session_id}_frame_{frame_id}.jpg"
            frame_filepath = os.path.join(UPLOADS_DIR, frame_filename)
            if not os.path.exists(frame_filepath):
                with open(frame_filepath, "wb") as f:
                    f.write(frame_bytes)

            # Base64 encode for APIs
            b64_frame = base64.b64encode(frame_bytes).decode("utf-8")
            
            # --- Tier 1: Local OCR Engine candidate extraction ---
            ocr_candidates = []
            ocr_text = ""
            ocr_res = {}
            try:
                from backend import _ocr_manager
                ocr_res = _ocr_manager.run_ocr(frame_bytes, frame_filename)
                if ocr_res.get("status") == "success" and ocr_res.get("text"):
                    ocr_text = ocr_res["text"].strip()
                    if ocr_text:
                        await self.log_audit_event("l12_ocr_extracted", f"Frame {frame_id}, source=local_ocr, length={len(ocr_text)}", db=db)
                        
                        # Extract parsed location features
                        locations = ocr_res.get("features", {}).get("locations", [])
                        for loc in locations:
                            if is_allowed_location_entity(loc):
                                ocr_candidates.append(loc)
                                
                        # Extract lines from OCR text that pass allowed entity filter
                        for line in ocr_text.split("\n"):
                            line_clean = line.strip()
                            if len(line_clean) > 4 and is_allowed_location_entity(line_clean):
                                ocr_candidates.append(line_clean)
                                
                        # Parse individual word tokens (length >= 3) and log each detected OCR token
                        raw_words = re.findall(r'\b[a-zA-Z]{3,}\b', ocr_text)
                        seen_words = set()
                        for w in raw_words:
                            w_upper = w.upper()
                            if w_upper not in seen_words:
                                seen_words.add(w_upper)
                                await self.log_audit_event("ocr_candidate_detected", f'"{w_upper}"', db=db)
            except Exception as ocr_err:
                logger.error(f"Local OCR run failed in L12 loop: {ocr_err}")

            # --- Tier 0: Moondream Local vision model candidate extraction ---
            await self.log_audit_event("l12_moondream_called", f"Frame {frame_id}, forensic landmark prompt", db=db)
            
            run_l9 = (frame_id == middle_frame_index)
            md_res = await self.query_moondream_local(b64_frame, run_l9_geoloc=run_l9)
            
            moondream_candidates = []
            l9_result_narrative = None
            
            if md_res and md_res.get("status") != "invalid_vlm_response":
                l9_result_narrative = md_res.get("l9_narrative")
                # Feed Moondream reasoning context as soft trace evidence (evidence only, never geocoded directly)
                if md_res.get("confidence_reasoning"):
                    supporting_evidence.append({
                        "frame_id": frame_label,
                        "tier": 0,
                        "evidence_type": "moondream_reasoning",
                        "description": md_res["confidence_reasoning"]
                    })
                
                # Extract candidates from VLM schema keys
                for cat in ["landmark_candidates", "building_candidates", "city_candidates", "country_candidates"]:
                    for cand in md_res.get(cat, []):
                        if is_allowed_location_entity(cand):
                            moondream_candidates.append({
                                "name": cand,
                                "category": cat
                            })
            else:
                if md_res and md_res.get("status") == "invalid_vlm_response":
                    await self.log_audit_event("landmark_candidate_rejected", f"Frame {frame_id} invalid VLM response schema", db=db)
                else:
                    await self.log_audit_event("l12_moondream_failed", f"Frame {frame_id} Moondream offline or error", db=db)

            # --- Candidate Fusion ---
            fused_candidates = [] # list of dicts: {"name": ..., "source": ..., "base_score": ..., "category": ...}
            
            # Add OCR candidates
            for ocr_cand in ocr_candidates:
                fused_candidates.append({
                    "name": ocr_cand,
                    "source": "ocr",
                    "base_score": 0.50,
                    "category": "landmark_candidates"
                })
                await self.log_audit_event("landmark_candidate_detected", f'"{ocr_cand}"', db=db)
                
            # Add Moondream candidates
            for md_cand in moondream_candidates:
                name = md_cand["name"]
                cat = md_cand["category"]
                
                duplicate = False
                for fc in fused_candidates:
                    if names_agree(name, fc["name"]):
                        fc["base_score"] = min(0.90, fc["base_score"] + 0.15)
                        fc["source"] = f"{fc['source']}_and_moondream"
                        duplicate = True
                        await self.log_audit_event("landmark_verified", f"OCR and Moondream candidates agree: '{fc['name']}' <=> '{name}'", db=db)
                        break
                
                if not duplicate:
                    fused_candidates.append({
                        "name": name,
                        "source": "moondream",
                        "base_score": 0.60 if cat == "landmark_candidates" else 0.50,
                        "category": cat
                    })
                    await self.log_audit_event("landmark_candidate_detected", f'"{name}"', db=db)

            # --- Evidence-Derived OCR Candidate Boosting ---
            if ocr_text:
                # Find all unique OCR tokens
                ocr_words_set = {w.upper() for w in re.findall(r'\b[a-zA-Z]{3,}\b', ocr_text)}
                ocr_confidence = ocr_res.get("confidence", 0.90)
                generic_terms = {"hotel", "palace", "building", "house", "tower", "bridge", "monument", "temple", "church", "cathedral", "castle", "station", "airport", "hall", "plaza", "square", "street", "road", "lake", "river", "mountain", "park"}
                
                for fc in fused_candidates:
                    name_clean = fc["name"]
                    cand_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', name_clean.lower()))
                    if not cand_words:
                        continue
                    
                    matches = cand_words.intersection({w.lower() for w in ocr_words_set})
                    if matches:
                        overlap_ratio = len(matches) / len(cand_words)
                        weighted_matches = sum(0.3 if w in generic_terms else 1.0 for w in matches)
                        uniqueness_score = weighted_matches / len(matches)
                        candidate_specificity = min(1.0, len(cand_words) / 4.0)
                        
                        ocr_boost = overlap_ratio * ocr_confidence * uniqueness_score * candidate_specificity * 0.40
                        
                        old_score = fc["base_score"]
                        fc["base_score"] = min(0.95, fc["base_score"] + ocr_boost)
                        fc["source"] = f"{fc['source']}_and_ocr_boosted"
                        
                        await self.log_audit_event(
                            "landmark_verified",
                            f"Candidate '{name_clean}' boosted by OCR matches. Overlap={overlap_ratio:.2f}, Conf={ocr_confidence:.2f}, Uniqueness={uniqueness_score:.2f}, Specificity={candidate_specificity:.2f}. Boost={ocr_boost:.3f} (score: {old_score:.2f} -> {fc['base_score']:.2f})",
                            db=db
                        )

            # Keep track of OCR signals for database persistence
            if ocr_text:
                ocr_signals.append({
                    "text": ocr_text,
                    "source": "local_ocr",
                    "confidence": 0.90,
                    "frame_id": frame_label,
                    "geocoding_status": "fused"
                })

            # --- SerpApi Google Lens Verification ---
            serp_kg_title = None
            serp_visual_matches = []
            resolved_t2 = False
            
            # Query SerpApi when we have candidates or the quality score is high
            should_query_serpapi = (len(fused_candidates) > 0) or (quality_score > 0.80)
            
            if should_query_serpapi:
                stats["frames_unresolved"] += 1
                token = secrets.token_urlsafe(16)
                temp_tokens[token] = {
                    "file_path": frame_filepath,
                    "expiry": time.time() + 120
                }
                
                t2_res = await self.query_serpapi_google_lens(token, p_hash, ignore_cache=ignore_cache)
                temp_tokens.pop(token, None)
                
                kg = t2_res.get("knowledge_graph", [])
                vm = t2_res.get("visual_matches", [])
                
                has_kg = len(kg) > 0
                await self.log_audit_event("serpapi_query", "", db=db)
                await self.log_audit_event("l12_serpapi_result", f"Frame {frame_id}, knowledge_graph={has_kg}, visual_matches={len(vm)}", db=db)
                
                if kg:
                    title = kg[0].get("title", "")
                    subtitle = kg[0].get("subtitle", "")
                    if title and is_allowed_location_entity(title):
                        serp_kg_title = title
                        await self.log_audit_event("landmark_verified", f"SerpApi Knowledge Graph returned: '{title}' ({subtitle})", db=db)
                        await self.log_audit_event("knowledge_graph_match", f'"{title}"', db=db)
                
                for idx_vm, match in enumerate(vm[:5]):
                    title = match.get("title", "")
                    if title and is_allowed_location_entity(title):
                        serp_visual_matches.append({
                            "title": title,
                            "rank": idx_vm
                        })
                        
            # --- Cross-Validation & Geocoding ---
            for fc in fused_candidates:
                name = fc["name"]
                verified = False
                verification_source = ""
                
                # Check against SerpApi Knowledge Graph
                if serp_kg_title and names_agree(name, serp_kg_title):
                    verified = True
                    verification_source = "serpapi_knowledge_graph"
                    name = serp_kg_title # Align name to authoritative title
                
                # Check against top Visual Matches
                if not verified:
                    for vm_item in serp_visual_matches:
                        if names_agree(name, vm_item["title"]):
                            verified = True
                            verification_source = f"serpapi_visual_match_rank_{vm_item['rank']}"
                            name = vm_item["title"] # Align name to visual match title
                            break
                
                # Calculate final confidence score
                if verified:
                    fc["verified"] = True
                    fc["verification_source"] = verification_source
                    boost = 0.25 if "knowledge_graph" in verification_source else 0.15
                    fc["final_score"] = min(0.99, fc["base_score"] + boost)
                    await self.log_audit_event("landmark_verified", f"Candidate '{fc['name']}' verified via {verification_source}. Score: {fc['final_score']:.2f}", db=db)
                    resolved_t2 = True
                else:
                    fc["verified"] = False
                    fc["verification_source"] = None
                    fc["final_score"] = max(0.25, fc["base_score"] - 0.15) # Penalized unverified candidate
                    await self.log_audit_event("landmark_unverified", f"Candidate '{fc['name']}' not verified by SerpApi", db=db)
                    
                # Geocode (verified and unverified candidates alike; unverified kept as low confidence secondary evidence)
                lat, lng, osm_details = await self.geocode_text(name)
                if lat is not None and lng is not None:
                    ld_entry = {
                        "label": name,
                        "source": fc["source"],
                        "score": fc["final_score"],
                        "lat": lat,
                        "lng": lng,
                        "frame_id": frame_label,
                        "geocoded": True,
                        "verified": fc["verified"],
                        "verification_source": fc["verification_source"],
                        "supporting_evidence": f"Candidate: '{fc['name']}'. Source: {fc['source']}. Verified: {fc['verified']}. Score: {fc['final_score']:.2f}."
                    }
                    detected_landmarks.append(ld_entry)
                    
                    final_candidates.append({
                        "lat": lat,
                        "lng": lng,
                        "source": fc["source"] + ("_landmark" if fc["category"] == "landmark_candidates" else "_location"),
                        "raw_signal": name,
                        "confidence": fc["final_score"],
                        "frame_id": frame_label,
                        "timestamp": time.time(),
                        "verified": fc["verified"],
                        "verification_source": fc["verification_source"]
                    })
                    
                    if fc["source"] == "ocr" or "_and_moondream" in fc["source"]:
                        ocr_signals[-1]["resolved_location"] = osm_details.get("city", osm_details.get("country", ""))
                        ocr_signals[-1]["geocoding_status"] = "resolved"
                        stats["frames_tier1_resolved"] += 1

            # Directly geocode SerpApi Knowledge Graph if not already matched
            if serp_kg_title:
                already_matched = False
                for fc in fused_candidates:
                    if fc.get("verified") and fc.get("verification_source") == "serpapi_knowledge_graph":
                        already_matched = True
                        break
                if not already_matched:
                    lat, lng, osm_details = await self.geocode_text(serp_kg_title)
                    if lat is not None and lng is not None:
                        resolved_t2 = True
                        ld_entry = {
                            "label": serp_kg_title,
                            "source": "serpapi_knowledge_graph",
                            "score": 0.85,
                            "lat": lat,
                            "lng": lng,
                            "frame_id": frame_label,
                            "geocoded": True,
                            "verified": True,
                            "verification_source": "serpapi_knowledge_graph",
                            "supporting_evidence": "Authoritative SerpApi Knowledge Graph match directly geocoded."
                        }
                        detected_landmarks.append(ld_entry)
                        
                        final_candidates.append({
                            "lat": lat,
                            "lng": lng,
                            "source": "serpapi_knowledge_graph",
                            "raw_signal": serp_kg_title,
                            "confidence": 0.85 * SIGNAL_WEIGHTS["serpapi_knowledge_graph"],
                            "frame_id": frame_label,
                            "timestamp": time.time(),
                            "verified": True,
                            "verification_source": "serpapi_knowledge_graph"
                        })
                        
            # Record matching visual search matches for reporting
            for idx_vm, vm_item in enumerate(serp_visual_matches):
                visual_search_matches.append({
                    "title": vm_item["title"],
                    "source_type": "serpapi_visual_match",
                    "rank": vm_item["rank"],
                    "frame_id": frame_label,
                    "resolved_lat": None,
                    "resolved_lng": None
                })
                # If matched a candidate, associate the coordinates
                for fc in final_candidates:
                    if fc["frame_id"] == frame_label and names_agree(fc["raw_signal"], vm_item["title"]):
                        visual_search_matches[-1]["resolved_lat"] = fc["lat"]
                        visual_search_matches[-1]["resolved_lng"] = fc["lng"]
                        break

            if resolved_t2:
                stats["frames_tier2_resolved"] += 1

            return l9_result_narrative

        # Run pipeline stages concurrently for all budgeted frames
        l9_reports = await asyncio.gather(*(process_frame(f) for f in budget_keyframes))
        
        # Extract L9 visual geolocation report if available from keyframes, fallback to standard LLM visual report
        final_l9_narrative = next((r for r in l9_reports if r), None)

        # 3. Geospatial Clustering Engine: DBSCAN
        cluster_summary = {
            "total_candidates": len(final_candidates),
            "cluster_count": 0,
            "noise_points": 0,
            "dominant_cluster_id": -1,
            "dominant_cluster_member_count": 0
        }

        final_lat, final_lng = (None, None)
        accuracy_radius_km = 0.0
        dominant_cluster_id = -1
        
        cluster_results_db = []

        if final_candidates:
            # Prepare coord list: [(lat, lng, idx, confidence)]
            coords = [(c["lat"], c["lng"], i, c["confidence"]) for i, c in enumerate(final_candidates)]
            
            # Run DBSCAN
            labels = dbscan_haversine(coords, DBSCAN_EPSILON_KM, DBSCAN_MIN_SAMPLES)
            
            # Map DBSCAN labels back to candidates
            for idx, lbl in enumerate(labels):
                final_candidates[idx]["cluster_id"] = int(lbl)

            # Separate into clusters
            clusters = {}
            for idx, lbl in enumerate(labels):
                if lbl != -1:
                    clusters.setdefault(lbl, []).append(coords[idx])
            
            cluster_summary["cluster_count"] = len(clusters)
            cluster_summary["noise_points"] = labels.count(-1)

            # Identify dominant cluster (highest weighted member count)
            if clusters:
                cluster_weights = {}
                for lbl, members in clusters.items():
                    weight_sum = sum(m[3] for m in members)
                    cluster_weights[lbl] = weight_sum
                
                dominant_cluster_id = max(cluster_weights, key=cluster_weights.get)
                dominant_members = clusters[dominant_cluster_id]
                
                cluster_summary["dominant_cluster_id"] = int(dominant_cluster_id)
                cluster_summary["dominant_cluster_member_count"] = len(dominant_members)

                # Compute confidence-weighted centroid
                sum_lat = 0.0
                sum_lng = 0.0
                total_weight = 0.0
                for m in dominant_members:
                    lat, lng, _, weight = m
                    sum_lat += lat * weight
                    sum_lng += lng * weight
                    total_weight += weight
                
                if total_weight > 0.0:
                    final_lat = sum_lat / total_weight
                    final_lng = sum_lng / total_weight

                # Compute accuracy radius (max haversine distance to any dominant cluster member)
                for m in dominant_members:
                    dist = haversine_distance((final_lat, final_lng), (m[0], m[1]))
                    if dist > accuracy_radius_km:
                        accuracy_radius_km = dist

                # Setup cluster summaries for database and write audit trail
                for lbl, members in clusters.items():
                    m_lat = sum(m[0] for m in members) / len(members)
                    m_lng = sum(m[1] for m in members) / len(members)
                    cluster_results_db.append({
                        "cluster_id": int(lbl),
                        "member_count": len(members),
                        "weighted_member_count": float(cluster_weights[lbl]),
                        "centroid_lat": float(m_lat),
                        "centroid_lng": float(m_lng),
                        "is_dominant": (lbl == dominant_cluster_id)
                    })
                    await self.log_audit_event("cluster_created", f"Cluster {lbl} created with {len(members)} members", db=db)
            else:
                # All points are noise
                dominant_cluster_id = -1
        
        await self.log_audit_event(
            "l12_clustering_completed",
            f"Total candidates: {len(final_candidates)}, clusters: {cluster_summary['cluster_count']}, noise: {cluster_summary['noise_points']}",
            db=db
        )

        # 4. Resolve City/Region/Country details of final centroid via OpenCage
        final_city, final_region, final_country = (None, None, None)
        if final_lat is not None and final_lng is not None:
            c_lat, c_lng, osm_details = await self.geocode_text(f"{final_lat}, {final_lng}")
            if osm_details:
                final_city = osm_details.get("city") or osm_details.get("town") or osm_details.get("suburb")
                final_region = osm_details.get("state") or osm_details.get("county")
                final_country = osm_details.get("country")

        # 5. Composite Confidence Scoring
        confidence_details = {
            "overall": 0.0,
            "landmark": 0.0,
            "ocr": 0.0,
            "visual_search": 0.0,
            "cluster_quality": 0.0,
            "frame_corroboration": 0.0,
            "l0_l11_alignment": 1.0  # default alignment bonus
        }

        # Derive scoring components
        v_scores = [lm["score"] for lm in detected_landmarks if lm["source"] == "moondream"]
        confidence_details["landmark"] = sum(v_scores) / len(v_scores) if v_scores else 0.0

        kg_count = sum(1 for lm in detected_landmarks if lm["source"] == "serpapi_knowledge_graph")
        vm_count = len(visual_search_matches)
        confidence_details["visual_search"] = min(1.0, (kg_count * 0.85) + (vm_count * 0.15))

        ocr_scores = [sig["confidence"] for sig in ocr_signals]
        confidence_details["ocr"] = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 0.0

        frames_with_points = len(set(c["frame_id"] for c in final_candidates if c.get("cluster_id") == dominant_cluster_id))
        confidence_details["frame_corroboration"] = (frames_with_points / len(budget_keyframes)) if budget_keyframes else 0.0

        dom_members_count = cluster_summary["dominant_cluster_member_count"]
        tot_candidates = len(final_candidates)
        confidence_details["cluster_quality"] = (dom_members_count / tot_candidates) if tot_candidates else 0.0
        
        # Calculate overall weighted L12 confidence
        w_overall = (
            confidence_details["landmark"] * 0.35 +
            confidence_details["visual_search"] * 0.20 +
            confidence_details["ocr"] * 0.15 +
            confidence_details["frame_corroboration"] * 0.15 +
            confidence_details["cluster_quality"] * 0.15
        )
        confidence_details["overall"] = round(float(min(0.99, max(0.0, w_overall))), 2)

        # Multi-landmark Triangulation Proximity checks
        has_verified_member = False
        if dominant_cluster_id != -1:
            dom_candidates = [
                c for c in final_candidates 
                if c.get("cluster_id") == dominant_cluster_id
            ]
            has_verified_member = any(c.get("verified") for c in dom_candidates)
            
            dom_landmarks = [
                c for c in dom_candidates 
                if c["source"] in ("ocr", "serpapi_knowledge_graph", "serpapi_visual_match", "moondream_landmark") or "ocr" in c["source"] or "moondream" in c["source"] or "serpapi" in c["source"]
            ]
            distinct_landmarks = set(l["raw_signal"] for l in dom_landmarks)
            if len(distinct_landmarks) >= 2:
                # 1. Landmark count factor
                f_count = min(1.0, (len(distinct_landmarks) - 1) * 0.2)
                
                # 2. Inter-landmark distance factor (mean pairwise distance)
                coords_dom = [(c["lat"], c["lng"]) for c in dom_landmarks]
                pairwise_distances = []
                for i in range(len(coords_dom)):
                    for j in range(i + 1, len(coords_dom)):
                        pairwise_distances.append(haversine_distance(coords_dom[i], coords_dom[j]))
                mean_dist = sum(pairwise_distances) / len(pairwise_distances) if pairwise_distances else 0.0
                f_dist = math.exp(-mean_dist / DBSCAN_EPSILON_KM) if mean_dist > 0 else 1.0
                
                # 3. Cluster density
                density = len(dom_landmarks) / len(final_candidates) if final_candidates else 0.0
                
                # 4. Source confidence
                mean_source_conf = sum(c["confidence"] for c in dom_landmarks) / len(dom_landmarks) if dom_landmarks else 0.0
                
                # 5. Frame corroboration
                corrob = confidence_details["frame_corroboration"]
                
                # Calculate dynamic confidence boost
                dynamic_boost = round(float(f_count * f_dist * density * mean_source_conf * corrob * 0.5), 4)
                confidence_details["overall"] = round(float(min(0.99, confidence_details["overall"] + dynamic_boost)), 2)
                
                # Calculate dynamic radius reduction factor
                # If mean_dist is small, reduce radius more (up to 50%). If mean_dist is large, reduce less.
                radius_reduction_factor = max(0.3, min(0.9, 1.0 - (0.6 * math.exp(-mean_dist / 20.0))))
                accuracy_radius_km = round(accuracy_radius_km * radius_reduction_factor, 2)
                
                supporting_evidence.append({
                    "frame_id": "dominant_cluster",
                    "tier": 3,
                    "evidence_type": "triangulation_boost",
                    "description": f"Triangulation bonus applied: count_factor={f_count:.2f}, dist_factor={f_dist:.2f}, density={density:.2f}, source_conf={mean_source_conf:.2f}, corroboration={corrob:.2f}. Boost={dynamic_boost:.2f}. Radius reduction factor={radius_reduction_factor:.2f}."
                })
                await self.log_audit_event("triangulation_completed", f"Triangulation completed for dominant cluster: {len(distinct_landmarks)} distinct landmarks, boost={dynamic_boost:.2f}, radius={accuracy_radius_km}km", db=db)

        # --- FORENSIC ACCURACY REQUIREMENT ---
        is_resolved = True
        unresolved_reason = None
        if final_lat is None or final_lng is None or confidence_details["overall"] < 0.25:
            is_resolved = False
            unresolved_reason = "insufficient evidence"
        elif not has_verified_member:
            is_resolved = False
            unresolved_reason = "unverified candidates cannot serve as sole basis for final location"
        
        # Check conflicts
        if len(cluster_results_db) > 1:
            cluster_results_db.sort(key=lambda x: x["weighted_member_count"], reverse=True)
            if (cluster_results_db[0]["weighted_member_count"] - cluster_results_db[1]["weighted_member_count"]) < (tot_candidates * 0.10):
                is_resolved = False
                unresolved_reason = "conflicting evidence"

        if not is_resolved:
            result_envelope = {
                "status": "unresolved",
                "reason": unresolved_reason
            }
            await self.log_audit_event("final_location_generated", f"Pipeline completed: Status=unresolved, Reason={unresolved_reason}", db=db)
            return result_envelope

        # Formulate final response envelope
        result_envelope = {
            "estimated_location": {
                "city": final_city or "Unknown",
                "region": final_region or "Unknown",
                "country": final_country or "Unknown",
                "coordinates": {
                    "lat": final_lat,
                    "lng": final_lng,
                    "accuracy_radius_km": round(accuracy_radius_km, 2)
                }
            },
            "candidate_locations": [
                {
                    "lat": c["lat"],
                    "lng": c["lng"],
                    "source": c["source"],
                    "raw_signal": c["raw_signal"],
                    "confidence": round(c["confidence"], 2),
                    "frame_id": c["frame_id"],
                    "cluster_id": c.get("cluster_id", -1)
                }
                for c in final_candidates
            ],
            "landmarks_detected": detected_landmarks,
            "ocr_signals": ocr_signals,
            "visual_search_matches": visual_search_matches,
            "cluster_summary": cluster_summary,
            "confidence": confidence_details,
            "supporting_evidence": supporting_evidence,
            "pipeline_stats": stats
        }

        # 6. Persist to SQLite database using SQLAlchemy
        try:
            async with async_session() as persist_session:
                # Write to landmark_intelligence_sessions
                persist_session.add(LandmarkIntelligenceSession(
                    session_id=session_id,
                    final_lat=final_lat,
                    final_lng=final_lng,
                    accuracy_radius_km=round(accuracy_radius_km, 2),
                    final_city=final_city,
                    final_region=final_region,
                    final_country=final_country,
                    overall_confidence=confidence_details["overall"],
                    dominant_cluster_id=dominant_cluster_id,
                    total_frames_processed=len(budget_keyframes),
                    frames_tier1_resolved=stats["frames_tier1_resolved"],
                    frames_tier2_resolved=stats["frames_tier2_resolved"]
                ))
                
                # Write landmark detections
                for ld in detected_landmarks:
                    persist_session.add(LandmarkDetection(
                        session_id=session_id,
                        frame_id=ld["frame_id"],
                        landmark_label=ld["label"],
                        source=ld["source"],
                        raw_score=ld["score"],
                        lat=ld["lat"],
                        lng=ld["lng"],
                        geocoded=ld["geocoded"],
                        supporting_evidence=ld["supporting_evidence"]
                    ))

                # Write OCR detections
                for od in ocr_signals:
                    persist_session.add(OCRDetection(
                        session_id=session_id,
                        frame_id=od["frame_id"],
                        extracted_text=od["text"],
                        ocr_source=od["source"],
                        confidence=od["confidence"],
                        resolved_lat=None, # geocoded coordinates stored in candidate_locations
                        resolved_lng=None,
                        geocoding_status=od.get("geocoding_status", "skipped")
                    ))

                # Write DBSCAN clusters
                for cr in cluster_results_db:
                    persist_session.add(L12ClusterResult(
                        session_id=session_id,
                        cluster_id=cr["cluster_id"],
                        member_count=cr["member_count"],
                        weighted_member_count=cr["weighted_member_count"],
                        centroid_lat=cr["centroid_lat"],
                        centroid_lng=cr["centroid_lng"],
                        is_dominant=cr["is_dominant"]
                    ))

                await persist_session.commit()
                await self.log_audit_event("final_location_generated", f"{final_city}, {final_region}, {final_country}", db=db)
                await self.log_audit_event("l12_final_estimate_committed", f"L12 results successfully saved to Database", db=db)

        except Exception as db_err:
            logger.error(f"Failed to persist L12 database records: {db_err}")

        # Clean up video files from uploads
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception:
            pass

        return result_envelope
