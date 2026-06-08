import pytest
from ocr_manager import OCRManager

def test_ocr_manager_detection():
    manager = OCRManager(strict_mode=True)
    # Checks that it registers or checks dependencies without throwing exceptions
    assert manager.strict_mode is True

def test_ocr_manager_unavailability():
    manager = OCRManager(strict_mode=True)
    
    # Under strict mode, if we give it empty image bytes, it should return unavailable status
    res = manager.run_ocr(b'', "empty_image.png")
    assert res["status"] == "unavailable"
    assert res["reason"] == "ocr_unavailable"
    assert res["text"] == ""

def test_feature_extraction_routing():
    manager = OCRManager(strict_mode=True)
    # Mock some run_ocr result behavior using test wrapper if text is present
    ocr_text = "江戸前寿司 (Edomae Sushi) Chiyoda Japan JR EAST Rail Terminal. Watermark @kasamacura."
    
    from ocr_intelligence import extract_metadata_patterns, detect_logos_and_watermarks
    features = extract_metadata_patterns(ocr_text)
    logos = detect_logos_and_watermarks(ocr_text)
    
    assert "@kasamacura" not in features["usernames"] # regex looks for @handle without trailing dot
    assert "kasamacura" in features["usernames"]
    assert "Japan" in features["locations"]
    assert any(logo["logo"] == "Target Profile Watermark" for logo in logos)
