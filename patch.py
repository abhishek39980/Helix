import sys

with open("backend/backend.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update ForensicAnalysisResponse
old_model = """class ForensicAnalysisResponse(BaseModel):
    id: Optional[str] = None
    saved_path: Optional[str] = None
    filename: str
    md5: str
    phash: str
    dimensions: str
    exif: Dict[str, Any]
    vision_location_report: str
    mutation_tree: MutationTreeSchema
    temporal_analysis: Dict[str, Any]
    location_intelligence: Dict[str, Any]
    source_profile: SourceProfileSchema"""

new_model = """class ForensicAnalysisResponse(BaseModel):
    id: Optional[str] = None
    saved_path: Optional[str] = None
    filename: str
    md5: str
    phash: str
    dimensions: str
    exif: Dict[str, Any]
    vision_location_report: str
    mutation_tree: MutationTreeSchema
    temporal_analysis: Dict[str, Any]
    location_intelligence: Dict[str, Any]
    source_profile: SourceProfileSchema
    frame_hashes: List[str] = []
    video_analysis: Optional[Dict[str, Any]] = None"""

content = content.replace(old_model, new_model)


# 2. Add calculate_video_forensics before MAIN FILE PROCESSING PIPELINE
old_pipeline_header = """# ──────────────────────────────────────────────────────────────────────────────
# MAIN FILE PROCESSING PIPELINE
# ──────────────────────────────────────────────────────────────────────────────"""

calculate_video_forensics_code = """def calculate_video_forensics(video_path: str) -> dict:
    import cv2
    import imagehash
    from PIL import Image

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "video_phash": "Unavailable",
            "frame_hashes": [],
            "frames_sampled": 0,
            "duration": 0.0,
            "fps": 0.0,
            "scene_changes": []
        }

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0.0
    
    if duration < 10:
        sample_count = min(10, total_frames)
    elif duration < 60:
        sample_count = min(20, total_frames)
    else:
        sample_count = min(30, total_frames)
        
    frame_hashes = []
    
    if sample_count > 0 and total_frames > 0:
        step = max(1, total_frames // sample_count)
        for i in range(sample_count):
            frame_idx = i * step
            if frame_idx >= total_frames:
                frame_idx = total_frames - 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
                
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            h = imagehash.phash(pil_img)
            frame_hashes.append(str(h))
            
    cap.release()

    scene_changes = []
    for i in range(1, len(frame_hashes)):
        h1 = imagehash.hex_to_hash(frame_hashes[i-1])
        h2 = imagehash.hex_to_hash(frame_hashes[i])
        distance = h1 - h2
        if distance > 10:
            timestamp = (i * step) / fps if fps > 0 else 0.0
            scene_changes.append({
                "timestamp": round(timestamp, 2),
                "distance": distance
            })
            
    if frame_hashes:
        bit_counts = [0] * 64
        for h in frame_hashes:
            hash_obj = imagehash.hex_to_hash(h)
            bits = hash_obj.hash.flatten()
            for idx, bit in enumerate(bits):
                if bit:
                    bit_counts[idx] += 1
                    
        half_count = len(frame_hashes) / 2
        final_bits = [1 if count > half_count else 0 for count in bit_counts]
        
        hex_chars = []
        for i in range(0, 64, 4):
            val = (final_bits[i] << 3) | (final_bits[i+1] << 2) | (final_bits[i+2] << 1) | final_bits[i+3]
            hex_chars.append(f"{val:x}")
        video_phash = "".join(hex_chars)
    else:
        video_phash = "Unavailable"

    return {
        "video_phash": video_phash,
        "frame_hashes": frame_hashes,
        "frames_sampled": len(frame_hashes),
        "duration": round(duration, 2),
        "fps": round(fps, 2),
        "scene_changes": scene_changes
    }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN FILE PROCESSING PIPELINE
# ──────────────────────────────────────────────────────────────────────────────"""

content = content.replace(old_pipeline_header, calculate_video_forensics_code)


# 3. Update initialization in process_file_bytes
old_init = """        md5_hash = hashlib.md5(file_bytes).hexdigest()
        phash_str = "N/A (Video Stream Container)"
        dimensions = "Container Stream (Auto)"
        is_image = False
        geo_visual_report = \"\"\""""
old_init = old_init.replace('\"\"\"', '\"\"')

new_init = """        md5_hash = hashlib.md5(file_bytes).hexdigest()
        phash_str = "N/A (Video Stream Container)"
        dimensions = "Container Stream (Auto)"
        is_image = False
        geo_visual_report = ""
        frame_hashes = []
        video_analysis = None"""

content = content.replace(old_init, new_init)


# 4. Update the video branch in process_file_bytes
old_video_branch = """        elif is_video_ext:
            try:
                import tempfile
                import cv2
                import os as _os

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                cap = cv2.VideoCapture(tmp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                dimensions = f"{width}x{height}"
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
                ret, frame = cap.read()
                cap.release()
                try:
                    _os.remove(tmp_path)
                except Exception:
                    pass
                if ret:
                    _, buffer = cv2.imencode(".jpg", frame)
                    base64_img = base64.b64encode(buffer).decode("utf-8")
                    geo_visual_report = (
                        "**Forensic Video Frame Extraction (Middle Frame)**\\n\\n"
                        + perform_local_visual_geolocation(base64_img)
                    )
                else:
                    geo_visual_report = "Error: Failed to extract frame from video for geolocation."
            except Exception as vid_err:
                print(f"Error extracting video frame: {vid_err}")
                geo_visual_report = "Error processing video frame extraction pipeline." """
old_video_branch = old_video_branch.rstrip(" ")

new_video_branch = """        elif is_video_ext:
            try:
                import tempfile
                import cv2
                import os as _os

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                v_analysis = calculate_video_forensics(tmp_path)
                phash_str = v_analysis.get("video_phash", "Unavailable")
                frame_hashes = v_analysis.get("frame_hashes", [])
                video_analysis = {
                    "frames_sampled": v_analysis.get("frames_sampled", 0),
                    "duration": v_analysis.get("duration", 0.0),
                    "fps": v_analysis.get("fps", 0.0),
                    "scene_changes": v_analysis.get("scene_changes", [])
                }

                cap = cv2.VideoCapture(tmp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                dimensions = f"{width}x{height}"
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
                ret, frame = cap.read()
                cap.release()
                try:
                    _os.remove(tmp_path)
                except Exception:
                    pass
                if ret:
                    _, buffer = cv2.imencode(".jpg", frame)
                    base64_img = base64.b64encode(buffer).decode("utf-8")
                    geo_visual_report = (
                        "**Forensic Video Frame Extraction (Middle Frame)**\\n\\n"
                        + perform_local_visual_geolocation(base64_img)
                    )
                else:
                    geo_visual_report = "Error: Failed to extract frame from video for geolocation."
            except Exception as vid_err:
                print(f"Error extracting video frame: {vid_err}")
                geo_visual_report = "Error processing video frame extraction pipeline." """
new_video_branch = new_video_branch.rstrip(" ")

content = content.replace(old_video_branch, new_video_branch)


# 5. Update return dict
old_return = """                "website": source_profile.get("website", "") if source_profile else "",
                "join_date": source_profile.get("join_date", "") if source_profile else "",
                "tweet_source": tweet_source,
            },
        }

    except Exception as general_err:"""

new_return = """                "website": source_profile.get("website", "") if source_profile else "",
                "join_date": source_profile.get("join_date", "") if source_profile else "",
                "tweet_source": tweet_source,
            },
            "frame_hashes": frame_hashes,
            "video_analysis": video_analysis
        }

    except Exception as general_err:"""

content = content.replace(old_return, new_return)


# 6. Update generate_pdf_report_stream
old_pdf = """    story.append(Paragraph("2. Geolocation Intelligence Summary", h2_style))"""

new_pdf = """    if data.get("video_analysis"):
        story.append(Paragraph("2. Video Forensics Summary", h2_style))
        vid_data = data.get("video_analysis", {})
        vid_table = [
            [Paragraph("Frames Sampled", bold_body_style), Paragraph(str(vid_data.get("frames_sampled", 0)), body_style)],
            [Paragraph("Duration (sec)", bold_body_style), Paragraph(str(vid_data.get("duration", 0)), body_style)],
            [Paragraph("FPS", bold_body_style), Paragraph(str(vid_data.get("fps", 0)), body_style)],
            [Paragraph("Scene Changes Detected", bold_body_style), Paragraph(str(len(vid_data.get("scene_changes", []))), body_style)],
        ]
        
        frames = data.get("frame_hashes", [])
        if frames:
            top_10 = ", ".join(frames[:10])
            vid_table.append([Paragraph("First 10 Frame Hashes", bold_body_style), Paragraph(top_10, body_style)])
            
        t_vid = Table(vid_table, colWidths=[150, 400])
        t_vid.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_vid)
        story.append(Spacer(1, 15))
        
    story.append(Paragraph("3. Geolocation Intelligence Summary" if data.get("video_analysis") else "2. Geolocation Intelligence Summary", h2_style))"""

content = content.replace(old_pdf, new_pdf)

old_pdf_2 = """    story.append(Paragraph("3. Temporal & Posting Signature Analysis", h2_style))"""
new_pdf_2 = """    story.append(Paragraph("4. Temporal & Posting Signature Analysis" if data.get("video_analysis") else "3. Temporal & Posting Signature Analysis", h2_style))"""
content = content.replace(old_pdf_2, new_pdf_2)

old_pdf_3 = """    story.append(Paragraph("4. Disseminating Source Profile Summary", h2_style))"""
new_pdf_3 = """    story.append(Paragraph("5. Disseminating Source Profile Summary" if data.get("video_analysis") else "4. Disseminating Source Profile Summary", h2_style))"""
content = content.replace(old_pdf_3, new_pdf_3)


# 7. Update generate_csv_report_string
old_csv = """    writer.writerow(["Metadata", "Dimensions", data.get("dimensions", "Unknown")])"""

new_csv = """    writer.writerow(["Metadata", "Dimensions", data.get("dimensions", "Unknown")])
    
    if data.get("video_analysis"):
        vid_data = data.get("video_analysis", {})
        writer.writerow(["Video Forensics", "Frames Sampled", vid_data.get("frames_sampled", 0)])
        writer.writerow(["Video Forensics", "Duration", vid_data.get("duration", 0)])
        writer.writerow(["Video Forensics", "FPS", vid_data.get("fps", 0)])
        writer.writerow(["Video Forensics", "Scene Changes", len(vid_data.get("scene_changes", []))])
        frames = data.get("frame_hashes", [])
        if frames:
            writer.writerow(["Video Forensics", "First 10 Frame Hashes", ", ".join(frames[:10])])"""

content = content.replace(old_csv, new_csv)

with open("backend/backend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch successfully applied!")
