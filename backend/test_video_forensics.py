import pytest
from fastapi.testclient import TestClient
import os
import asyncio
from datetime import datetime, timezone

# Set environment vars for testing
os.environ["API_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_backend.db"

from backend import app, get_session_frame_hashes, set_session_frame_hashes
from db import get_db, AnalysisSession

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_sequence_distance():
    from backend import calculate_sequence_distance
    
    # Test identical sequences
    seq_a = ["8f2af8c2a8c2f8c2", "1a2b3c4d5e6f7a8b"]
    seq_b = ["8f2af8c2a8c2f8c2", "1a2b3c4d5e6f7a8b"]
    dist = calculate_sequence_distance(seq_a, seq_b)
    assert dist == 0.0
    
    # Test different sequences
    seq_c = ["ffffffffffffffff", "ffffffffffffffff"]
    dist_diff = calculate_sequence_distance(seq_a, seq_c)
    assert dist_diff > 0.0
    
    # Test empty sequences
    assert calculate_sequence_distance([], seq_a) == 64.0

def test_similarity_and_confidence():
    from backend import calculate_video_similarity_and_confidence
    
    phash_a = "8f2af8c2a8c2f8c2"
    phash_b = "8f2af8c2a8c2f8c2"
    seq_a = ["8f2af8c2a8c2f8c2"] * 10
    seq_b = ["8f2af8c2a8c2f8c2"] * 10
    
    # Identical videos
    res = calculate_video_similarity_and_confidence(phash_a, phash_b, seq_a, seq_b, 10.0, 10.0)
    assert res["similarity_score"] == 100.0
    assert res["confidence_score"] == 1.0
    assert res["classification"] == "Nearly identical"

    # Completely different videos
    phash_c = "70d5073d573d073d"
    seq_c = ["70d5073d573d073d"] * 10
    res_diff = calculate_video_similarity_and_confidence(phash_a, phash_c, seq_a, seq_c, 10.0, 60.0)
    assert res_diff["similarity_score"] < 50.0
    assert res_diff["classification"] == "Unrelated"

def test_storage_helpers():
    class MockSession:
        def __init__(self):
            self.frame_hashes = None
            
    sess = MockSession()
    assert get_session_frame_hashes(sess) == []
    
    set_session_frame_hashes(sess, ["hash1", "hash2"])
    assert get_session_frame_hashes(sess) == ["hash1", "hash2"]

def test_compare_endpoints(client):
    headers = {"X-API-Key": "test-secret-key"}
    
    # Test raw comparison
    payload = {
        "hash_a": "8f2af8c2a8c2f8c2",
        "hash_b": "8f2af8c2a8c2f8c2",
        "session_id_a": None,
        "session_id_b": None
    }
    
    resp = client.post("/api/compare-videos", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "similarity_score" in data
    assert data["classification"] == "Nearly identical"


def test_find_similar_videos_endpoint(client):
    headers = {"X-API-Key": "test-secret-key"}
    
    # Test similar search on a session that doesn't exist (returns 404)
    payload = {
        "session_id": "nonexistent-id"
    }
    resp = client.post("/api/find-similar-videos", json=payload, headers=headers)
    assert resp.status_code == 404


def test_build_dynamic_mutation_tree():
    import asyncio
    from backend import build_dynamic_mutation_tree
    
    async def run_tree_test():
        res = await build_dynamic_mutation_tree(
            current_session_id="test",
            current_phash="8f2af8c2a8c2f8c2",
            current_duration=10.0,
            current_dimensions="1280x720",
            current_frame_hashes=["8f2af8c2a8c2f8c2"],
            db=None
        )
        assert "variants" in res
        assert len(res["variants"]) > 0
        assert res["variants"][-1]["id"] == "current_uploaded"
        
    asyncio.run(run_tree_test())


def test_twitter_url_ingestion(client):
    headers = {"X-API-Key": "test-secret-key"}
    payload = {
        "url": "https://twitter.com/kasamacura/status/2046098263544357246"
    }
    resp = client.post("/api/analyze-url", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "video_analysis" in data
    assert data["video_analysis"] is not None
    assert data["phash"] != "N/A (Video Stream Container)"
    assert data["phash"] != "Unavailable"

