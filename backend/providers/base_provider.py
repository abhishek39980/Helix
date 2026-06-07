from abc import ABC, abstractmethod
from datetime import datetime

class SearchProvider(ABC):
    """Abstract base class representing a global OSINT or visual search provider."""
    
    @abstractmethod
    async def search_by_image(self, keyframe_bytes: bytes, filename: str = "") -> list[dict]:
        """
        Executes a reverse visual search using keyframe image bytes.
        Returns a list of standardized dicts:
        [
            {
                "platform": str,
                "url": str,
                "username": str,
                "timestamp": datetime,
                "caption": str,
                "ocr_text": str | None
            }
        ]
        """
        pass

    @abstractmethod
    async def search_by_metadata(self, query: str) -> list[dict]:
        """
        Executes a metadata search (e.g. usernames, captions, OCR text).
        Returns a list of standardized dicts with the same schema.
        """
        pass

    def normalize_platform(self, url: str) -> str:
        """Determines the platform name based on the URL structure."""
        url_lower = url.lower()
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "X (Twitter)"
        elif "t.me" in url_lower or "telegram" in url_lower:
            return "Telegram"
        elif "reddit.com" in url_lower:
            return "Reddit"
        elif "tiktok.com" in url_lower:
            return "TikTok"
        elif "github.com" in url_lower:
            return "GitHub"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "YouTube"
        return "Web"
