import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextvars import ContextVar

# Import service and the dbscan function
from visual_location_intelligence import VisualLocationIntelligenceService, dbscan_haversine

# Mock context var for requests
request_id_var = ContextVar("request_id", default="test_req_123")

@pytest.fixture
def service():
    return VisualLocationIntelligenceService(request_id_var)

@pytest.mark.anyio
async def test_prioritize_keyframes(service):
    # Setup keyframes list: (frame_id, frame_bytes, p_hash)
    keyframes = [
        (0, b'f0', 'f4c2e8e99b0d33e1'),
        (10, b'f1', '12c2e8e99b0d3322'),
        (20, b'f2', '88c2e8e99b0d3355'),
        (30, b'f3', '88c2e8e99b0d3356'),
        (40, b'f4', '88c2e8e99b0d3357'),
        (50, b'f5', '88c2e8e99b0d3358'),
    ]
    
    # Mock helper calls
    mock_ocr = MagicMock()
    mock_ocr.run_ocr.return_value = {"status": "failed"}

    with patch('visual_location_intelligence.MAX_KEYFRAMES_PER_VIDEO', 3), \
         patch('cv2.imdecode', return_value=None), \
         patch('backend._ocr_manager', mock_ocr), \
         patch.object(service, 'query_moondream_local', AsyncMock(return_value={})):
        
        prioritized = await service.prioritize_keyframes(keyframes, "session_test")
        assert len(prioritized) == 3
        # Should take start, middle, end index
        indices = [k[0] for k in prioritized]
        assert 0 in indices
        assert 50 in indices

@pytest.mark.anyio
async def test_geocode_text_caching(service):
    # Reset geocode cache
    service.geocode_cache = {}
    service.geocode_calls_count = 0
    
    # Mock backend._resolver
    mock_resolver = AsyncMock()
    mock_resolver.resolve_entity.return_value = {
        "lat": 35.6895,
        "lng": 139.6917,
        "city": "Tokyo",
        "state": "Tokyo Prefecture",
        "country": "Japan"
    }
    
    with patch('backend._resolver', mock_resolver):
        # Call geocode
        lat, lng, details = await service.geocode_text("Edomae Sushi Chiyoda")
        assert lat == 35.6895
        assert lng == 139.6917
        assert details["city"] == "Tokyo"
        
        # Verify cached
        assert "Edomae Sushi Chiyoda" in service.geocode_cache
        
        # Call again, should return cached values without calling resolver
        mock_resolver.resolve_entity.reset_mock()
        lat2, lng2, details2 = await service.geocode_text("Edomae Sushi Chiyoda")
        assert lat2 == 35.6895
        mock_resolver.resolve_entity.assert_not_called()

@pytest.mark.anyio
async def test_dbscan_clustering():
    # Setup coordinates: [(lat, lng, index, confidence)]
    coords = [
        (35.6895, 139.6917, 0, 0.9),
        (35.6890, 139.6910, 1, 0.8),
        (35.6900, 139.6920, 2, 0.85),
        # Noise point far away (e.g. London)
        (51.5074, -0.1278, 3, 0.7),
    ]
    
    # Run dbscan_haversine directly (eps=50km, min_samples=2)
    labels = dbscan_haversine(coords, eps_km=50.0, min_samples=2)
    
    # Check that first 3 points are in the same cluster, and London is noise (-1)
    assert labels[0] == 0
    assert labels[1] == 0
    assert labels[2] == 0
    assert labels[3] == -1

@pytest.mark.anyio
async def test_pipeline_unresolved_under_confidence(service):
    # Test case when no candidates are resolved
    with patch.object(service, 'extract_scene_keyframes', AsyncMock(return_value=[(0, b'fake', 'hash', 0.90)])), \
         patch.object(service, 'geocode_text', AsyncMock(return_value=(None, None, {}))), \
         patch.object(service, 'query_moondream_local', AsyncMock(return_value={})), \
         patch.object(service, 'query_google_vision', AsyncMock(return_value={})), \
         patch.object(service, 'query_serpapi_google_lens', AsyncMock(return_value={"knowledge_graph": [], "visual_matches": []})):
        
        result = await service.execute_l12_pipeline(b'fake_bytes', "test_video.mp4", is_video=True, session_id="session_unres")
        assert result["status"] == "unresolved"
        assert result["reason"] == "insufficient evidence"

@pytest.mark.anyio
async def test_parse_moondream_json():
    from visual_location_intelligence import parse_moondream_json
    # 1. Standard JSON
    res = parse_moondream_json('{"landmark_candidates": ["Taj Mahal"], "building_candidates": [], "city_candidates": [], "country_candidates": [], "confidence_reasoning": "mausoleum"}')
    assert len(res["landmark_candidates"]) == 1
    assert res["landmark_candidates"][0] == "Taj Mahal"
    assert res["confidence_reasoning"] == "mausoleum"

    # 2. Markdown wrapped
    res_md = parse_moondream_json('```json\n{"landmark_candidates": ["Gateway of India"], "building_candidates": [], "city_candidates": [], "country_candidates": [], "confidence_reasoning": "arch"}\n```')
    assert len(res_md["landmark_candidates"]) == 1
    assert res_md["landmark_candidates"][0] == "Gateway of India"

    # 3. Soft repair (trailing comma)
    res_repair = parse_moondream_json('{\n  "landmark_candidates": [\n    "London Bridge",\n  ],\n  "confidence_reasoning": "river",\n}')
    assert len(res_repair["landmark_candidates"]) == 1
    assert res_repair["landmark_candidates"][0] == "London Bridge"

    # 4. Invalid response status (broken JSON)
    res_fallback = parse_moondream_json('Landmarks detected: Taj Mahal Palace (clearly), and maybe Gateway of India (possibly).')
    assert res_fallback["status"] == "invalid_vlm_response"

@pytest.mark.anyio
async def test_calculate_image_quality():
    import numpy as np
    from visual_location_intelligence import calculate_image_quality
    # Create simple 100x100 white image
    img = np.ones((100, 100), dtype=np.uint8) * 255
    score = calculate_image_quality(img, entropy=4.0)
    assert 0.0 <= score <= 1.0

@pytest.mark.anyio
async def test_names_agree():
    from visual_location_intelligence import names_agree
    assert names_agree("Taj Mahal Palace Hotel", "Taj Mahal Palace") is True
    assert names_agree("Taj Mahal", "Eiffel Tower") is False
    assert names_agree("Edomae Sushi Tokyo", "edomae sushi") is True
    assert names_agree("Gateway of India Mumbai", "Gateway of India") is True
    assert names_agree("Taj Mahal Palace Hotel", "Taj Mahal Palace Hotel Mumbai") is True
    assert names_agree("Gateway of India", "Gateway of India Monument") is True

@pytest.mark.anyio
async def test_location_entity_filtering():
    from visual_location_intelligence import is_allowed_location_entity
    # Allowed location entities
    assert is_allowed_location_entity("Taj Mahal Palace Hotel") is True
    assert is_allowed_location_entity("Mumbai") is True
    assert is_allowed_location_entity("Eiffel Tower") is True
    
    # Rejected entities
    assert is_allowed_location_entity("http://example.com") is False
    assert is_allowed_location_entity("example.org") is False
    assert is_allowed_location_entity("javascript") is False
    assert is_allowed_location_entity("terms of service") is False
    assert is_allowed_location_entity("nature") is False
    assert is_allowed_location_entity("avian visitors") is False
    assert is_allowed_location_entity("large ornate building") is False

@pytest.mark.anyio
async def test_dynamic_triangulation_math():
    from visual_location_intelligence import haversine_distance
    d = haversine_distance((18.9219, 72.8347), (18.9220, 72.8348))
    assert d < 1.0 # Less than 1km apart
