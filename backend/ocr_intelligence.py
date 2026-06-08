import re
import logging
from PIL import Image
import io

logger = logging.getLogger("helix.ocr")

# Flag indicating whether a real OCR engine is loaded
_ocr_engine_loaded = False
_easyocr_reader = None
_paddle_ocr = None


def extract_metadata_patterns(text: str) -> dict:
    """Parses text content to extract usernames, URLs, hashtags, domains, locations, and phone numbers."""
    features = {
        "usernames": [],
        "urls": [],
        "hashtags": [],
        "domains": [],
        "phone_numbers": [],
        "locations": []
    }
    if not text:
        return features

    # Usernames (@handle)
    features["usernames"] = list(set(re.findall(r"@([a-zA-Z0-9_]{1,15})", text)))

    # URLs
    raw_urls = re.findall(r"https?://[^\s\)\]]+", text)
    cleaned_urls = [u.rstrip('.,;?!)"') for u in raw_urls]
    features["urls"] = list(set(cleaned_urls))

    # Hashtags
    features["hashtags"] = list(set(re.findall(r"#(\w+)", text)))

    # Domains (simplistic match)
    features["domains"] = list(set(re.findall(r"\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b", text)))
    # Filter out common false positives
    features["domains"] = [d for d in features["domains"] if not d.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mov'))]

    # Phone numbers
    features["phone_numbers"] = list(set(re.findall(r"\+?\b\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b", text)))

    # Location references (simple list matching)
    locations_db = ["Tokyo", "Chiyoda", "Japan", "Mumbai", "Delhi", "India", "London", "UK", "New York", "USA", "California"]
    found_locs = []
    text_lower = text.lower()
    for loc in locations_db:
        if loc.lower() in text_lower:
            found_locs.append(loc)
    features["locations"] = list(set(found_locs))

    return features


def detect_logos_and_watermarks(text: str) -> list:
    """Detects social media networks, news brands, or transport lines in text."""
    detected = []
    if not text:
        return detected

    brand_signals = [
        (r"\b(cnn|cable news network)\b", "CNN", 0.95),
        (r"\b(bbc|british broadcasting)\b", "BBC", 0.95),
        (r"\b(telegram|t\.me)\b", "Telegram Watermark", 0.90),
        (r"\b(tiktok|tik tok)\b", "TikTok Logo", 0.90),
        (r"\b(twitter|x\.com)\b", "X (Twitter) Logo", 0.90),
        (r"\b(jr east|east japan rail|yamanote)\b", "East Japan Railway (JR EAST)", 0.92),
        (r"\b(kasamacura|sushi_forensics)\b", "Target Profile Watermark", 0.88),
    ]

    text_lower = text.lower()
    for pattern, name, confidence in brand_signals:
        if re.search(pattern, text_lower):
            detected.append({
                "logo": name,
                "confidence": confidence
            })
            
    return detected


def perform_ocr_on_image(image_bytes: bytes, filename: str = "") -> dict:
    """
    Orchestrates OCR extraction.
    Routes execution to OCRManager to avoid fabricated demo/simulation states.
    """
    from ocr_manager import OCRManager
    import os
    strict_mode = os.getenv("FORENSIC_STRICT_MODE", "true").lower() == "true"
    
    # Instantiate or run OCRManager
    manager = OCRManager(strict_mode=strict_mode)
    return manager.run_ocr(image_bytes, filename)

