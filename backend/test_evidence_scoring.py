import pytest
from datetime import datetime, timezone
from evidence import Evidence
from evidence_scoring import EvidenceScoringEngine

def test_single_active_layer_cap():
    engine = EvidenceScoringEngine(strict_mode=True)
    
    # 1. Test case: Only 1 active layer (Explicit Location)
    evidence_list = [
        Evidence(
            source="explicit_location_geocoder",
            source_type="profile_location",
            collection_method="api_query",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.90,
            value={"country": "Japan"}
        )
    ]
    
    res = engine.evaluate_location_confidence(evidence_list)
    assert res["country"] == "Japan"
    # Even if reliability is 90%, confidence must be capped at 40% (0.40) because only 1 active layer is present
    assert res["confidence"] <= 0.40
    assert "Capped at 40%" in res["explanation"]["summary"]

def test_two_active_layers_cap():
    engine = EvidenceScoringEngine(strict_mode=True)
    
    # 2. Test case: Only 2 active layers (Explicit + NER)
    evidence_list = [
        Evidence(
            source="explicit_location_geocoder",
            source_type="profile_location",
            collection_method="api_query",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.90,
            value={"country": "Japan"}
        ),
        Evidence(
            source="spaCy NER",
            source_type="ner_entity",
            collection_method="api_query",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.80,
            value={"country": "Japan"}
        )
    ]
    
    res = engine.evaluate_location_confidence(evidence_list)
    assert res["country"] == "Japan"
    # Confidence must be capped at 65% (0.65) because only 2 active layers are present
    assert res["confidence"] <= 0.65
    assert "Capped at 65%" in res["explanation"]["summary"]

def test_three_corroborating_layers_boost():
    engine = EvidenceScoringEngine(strict_mode=True)
    
    # 3. Test case: 3 corroborating layers (Explicit + NER + Language)
    evidence_list = [
        Evidence(
            source="explicit_location_geocoder",
            source_type="profile_location",
            collection_method="api_query",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.90,
            value={"country": "Japan"}
        ),
        Evidence(
            source="spaCy NER",
            source_type="ner_entity",
            collection_method="api_query",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.80,
            value={"country": "Japan"}
        ),
        Evidence(
            source="language_analyzer",
            source_type="language_script",
            collection_method="text_analysis",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=0.70,
            value={"country": "Japan"}
        )
    ]
    
    res = engine.evaluate_location_confidence(evidence_list)
    assert res["country"] == "Japan"
    # Boosted to 80%+ because 3 corroborating layers are present
    assert res["confidence"] >= 0.80
    assert "Boosted to 80%+" in res["explanation"]["summary"]
