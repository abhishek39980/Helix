from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class Evidence:
    source: str             # e.g., "Nitter", "EXIF", "Wikidata"
    source_type: str        # e.g., "profile", "ocr", "metadata", "visual"
    collection_method: str  # e.g., "scraping", "api", "local"
    timestamp: str          # UTC ISO timestamp
    reliability: float      # score between 0.0 and 1.0
    value: Any              # the extracted value (dict, list, str, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)
