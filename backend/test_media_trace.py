import pytest
from fastapi.testclient import TestClient
import os
import asyncio
from datetime import datetime, timezone

# Set testing environment variables
os.environ["API_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_backend.db"

from backend import app
from db import get_db, TraceJob, AnalysisSession
from ocr_intelligence import extract_metadata_patterns, detect_logos_and_watermarks
from audio_fingerprint import calculate_audio_hash
from media_trace_service import (
    calculate_frame_entropy, evaluate_similarity, 
    classify_mutation, PropagationGraphBuilder
)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_entropy_calculation():
    # Construct a solid mock image frame (black frame)
    black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    entropy = calculate_frame_entropy(black_frame)
    # A single solid color should have 0 entropy mathematically
    assert entropy == 0.0

    # Create random noise frame (high entropy)
    noise_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    noise_entropy = calculate_frame_entropy(noise_frame)
    assert noise_entropy > 0.0

def test_ocr_pattern_extraction():
    text = "Find me at @sushi_forensics. Visit http://sushi.jp/provenance. JR EAST Chiyoda Line. Contact +81-3-1234-5678 #OSINT"
    features = extract_metadata_patterns(text)
    
    assert "@sushi_forensics" not in features["usernames"] # regex extracts the clean handle without @
    assert "sushi_forensics" in features["usernames"]
    assert "http://sushi.jp/provenance" in features["urls"]
    assert "OSINT" in features["hashtags"]
    assert "sushi.jp" in features["domains"]
    assert "Chiyoda" in features["locations"]

def test_logo_watermark_detection():
    text = "Watermark @kasamacura. Broadcasted live on CNN."
    logos = detect_logos_and_watermarks(text)
    
    logo_names = [item["logo"] for item in logos]
    assert "CNN" in logo_names
    assert "Target Profile Watermark" in logo_names

def test_audio_fingerprint_fallback():
    # Test on a nonexistent path
    hash_val = calculate_audio_hash("nonexistent_video.mp4")
    assert hash_val == "Unavailable"

def test_similarity_scoring_engine():
    ref_phash = "f4c2e8e99b0d33e1"
    cand_phash = "f4c2e8e99b0d33e1"
    ref_keyframes = ["f4c2e8e99b0d33e1", "12c2e8e99b0d3322", "88c2e8e99b0d3355"]
    cand_keyframes = ["f4c2e8e99b0d33e1", "12c2e8e99b0d3322", "88c2e8e99b0d3355"]
    ref_scenes = ["f4c2e8e99b0d33e1"]
    cand_scenes = ["f4c2e8e99b0d33e1"]
    ref_dur, cand_dur = 10.0, 10.0
    ref_meta, cand_meta = "Edomae sushi JR East", "Edomae sushi JR East"

    score, confidence, signals = evaluate_similarity(
        ref_phash, cand_phash,
        ref_keyframes, cand_keyframes,
        ref_scenes, cand_scenes,
        ref_dur, cand_dur,
        ref_meta, cand_meta
    )
    
    assert score == 1.0
    assert confidence == 1.0
    assert signals["keyframe_similarity"] == 1.0

def test_mutation_classifier():
    signals = {
        "keyframe_similarity": 1.0,
        "video_phash": 1.0,
        "scene_alignment": 1.0,
        "duration_similarity": 1.0,
        "metadata_similarity": 1.0
    }
    
    mutation, confidence = classify_mutation(1.0, signals, 10.0, 10.0)
    assert mutation == "Exact Duplicate"

    # Test re-encoded signature
    signals_re = {
        "keyframe_similarity": 0.90,
        "video_phash": 0.85,
        "scene_alignment": 0.90,
        "duration_similarity": 1.0,
        "metadata_similarity": 0.90
    }
    mutation_re, _ = classify_mutation(0.89, signals_re, 10.0, 10.0)
    assert mutation_re == "Re-Encoded"

def test_graph_builder():
    occurrences = [
        {
            "platform": "Telegram",
            "username": "kasamacura",
            "timestamp": datetime(2026, 6, 3, 12, 1, tzinfo=timezone.utc),
            "similarity_score": 0.98,
            "mutation_type": "Exact Duplicate"
        }
    ]
    graph = PropagationGraphBuilder.build(occurrences, "test_video.mp4")
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1

def test_trace_endpoints_lifecycle(client):
    headers = {"X-API-Key": "test-secret-key"}
    
    # Pre-populate session
    # 1. Create a case
    resp = client.post(
        "/api/cases",
        json={"name": "Trace Verification Case", "description": "Verify OSINT tracking"},
        headers=headers
    )
    assert resp.status_code == 200
    case_id = resp.json()["id"]

    # 2. Add finished session record
    # Note: We must insert it directly or simulate it.
    # Let's verify that the trace jobs failover/errors behave correctly on missing sessions.
    resp_trace = client.post(f"/api/analysis-sessions/invalid-session-uuid/global-trace", headers=headers)
    assert resp_trace.status_code == 404

    # 3. Test URL safety check on direct trace
    payload_bad = {
        "url": "http://169.254.169.254/metadata",  # SSRF Blocked URL
        "case_id": case_id
    }
    resp_ssrf = client.post("/api/global-trace/url", json=payload_bad, headers=headers)
    assert resp_ssrf.status_code == 400

import numpy as np
