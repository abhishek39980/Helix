import pytest
from unittest.mock import AsyncMock, MagicMock
from visual_geolocation import VisualGeolocationEngine

@pytest.mark.anyio
async def test_visual_geolocate_keyframe():
    ocr_manager = MagicMock()
    ocr_manager.run_ocr.return_value = {
        "status": "success",
        "text": "Edomae Sushi Chiyoda Tokyo",
        "provider": "paddleocr",
        "confidence": 0.95,
        "logos": [{"logo": "JR East", "confidence": 0.88}]
    }
    
    resolver = AsyncMock()
    # Mock JR East -> Japan, Edomae Sushi -> Japan
    resolver.resolve_entity.side_effect = lambda entity: {
        "JR East": {"country": "Japan", "source": "Wikidata"},
        "Edomae Sushi": {"country": "Japan", "source": "Wikidata"},
        "Edomae Sushi Chiyoda Tokyo": {"country": "Japan", "source": "OpenStreetMap"}
    }.get(entity)
    
    ner_engine = AsyncMock()
    ner_engine.resolve_text_entities.return_value = []
    
    engine = VisualGeolocationEngine(ocr_manager, resolver, ner_engine)
    evidence_list = await engine.geolocate_keyframe(b'fake_bytes', "frame.png", "session_123")
    
    assert len(evidence_list) >= 2
    # One is OCR text itself, one is the brand signature resolver match
    sources = [ev.source for ev in evidence_list]
    assert "paddleocr" in sources
    assert "brand_resolver" in sources
    assert any(ev.value.get("country") == "Japan" for ev in evidence_list)
