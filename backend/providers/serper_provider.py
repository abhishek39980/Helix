import os
import re
import logging
from datetime import datetime, timezone, timedelta
from providers.base_provider import SearchProvider

logger = logging.getLogger("helix.providers.serper")

class SerperProvider(SearchProvider):
    """Metadata-based search provider using Google Serper API."""

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY", "")

    async def search_by_image(self, keyframe_bytes: bytes, filename: str = "") -> list[dict]:
        """
        Since Google Lens scraping is fragile, we perform a visual proxy search:
        We extract text patterns from the keyframe, then search the web for those signatures.
        """
        from ocr_intelligence import perform_ocr_on_image
        ocr_res = perform_ocr_on_image(keyframe_bytes, filename)
        text = ocr_res.get("text", "")
        
        if not text or len(text.strip()) < 5:
            logger.info("No substantial OCR text found in keyframe for Serper search.")
            return []

        # Run metadata search on the extracted OCR text
        return await self.search_by_metadata(text)

    async def search_by_metadata(self, query: str) -> list[dict]:
        """Queries Serper API with the text string, targeting public platforms."""
        if not self.api_key:
            logger.warning("SERPER_API_KEY not set. Skipping Serper web search.")
            return []

        # Clean query: strip special characters and limit length
        clean_query = re.sub(r'[^\w\s@#.-]', '', query).strip()
        if not clean_query:
            return []
        
        # Take first 100 characters to keep search query focused
        clean_query = clean_query[:100]
        
        # Enforce search targeting main platforms
        search_query = f'"{clean_query}" (site:x.com OR site:twitter.com OR site:t.me OR site:reddit.com OR site:tiktok.com)'
        logger.info(f"Executing Serper OSINT metadata search: {search_query}")

        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": search_query,
            "num": 10
        }

        matches = []
        try:
            from backend import get_async_client
            client = get_async_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get("organic", [])
                for r in results:
                    link = r.get("link", "")
                    snippet = r.get("snippet", "")
                    title = r.get("title", "")
                    date_str = r.get("date", "")  # Google indexed date e.g. "3 days ago", "May 10, 2026"
                    
                    if not link:
                        continue

                    # Parse platform
                    platform = self.normalize_platform(link)
                    
                    # Parse username from URL
                    username = "anonymous"
                    link_lower = link.lower()
                    if "x.com" in link_lower or "twitter.com" in link_lower:
                        m = re.search(r"(?:twitter|x)\.com/([^/]+)", link, re.IGNORECASE)
                        if m:
                            username = f"@{m.group(1)}"
                    elif "t.me" in link_lower:
                        m = re.search(r"t\.me/([^/]+)", link, re.IGNORECASE)
                        if m:
                            username = f"@{m.group(1)}"
                    elif "reddit.com" in link_lower:
                        m = re.search(r"reddit\.com/(?:r|user)/([^/]+)", link, re.IGNORECASE)
                        if m:
                            username = f"u/{m.group(1)}"
                    elif "tiktok.com" in link_lower:
                        m = re.search(r"tiktok\.com/@([^/?]+)", link, re.IGNORECASE)
                        if m:
                            username = f"@{m.group(1)}"

                    # Parse timestamp or fallback to current time minus delta
                    parsed_dt = self._parse_google_date(date_str)

                    matches.append({
                        "platform": platform,
                        "url": link,
                        "username": username,
                        "timestamp": parsed_dt,
                        "caption": snippet or title,
                        "ocr_text": clean_query
                    })
        except Exception as e:
            logger.error(f"Serper metadata query failed: {e}")

        return matches

    def _parse_google_date(self, date_str: str) -> datetime:
        """Helper to parse Google relative dates (e.g. '3 days ago') or absolute dates to UTC datetime."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not date_str:
            return now

        date_str = date_str.lower().strip()
        try:
            if "hour" in date_str:
                m = re.search(r"(\d+)", date_str)
                hours = int(m.group(1)) if m else 1
                return now - timedelta(hours=hours)
            elif "day" in date_str:
                m = re.search(r"(\d+)", date_str)
                days = int(m.group(1)) if m else 1
                return now - timedelta(days=days)
            elif "week" in date_str:
                m = re.search(r"(\d+)", date_str)
                weeks = int(m.group(1)) if m else 1
                return now - timedelta(weeks=weeks)
            elif "month" in date_str:
                m = re.search(r"(\d+)", date_str)
                months = int(m.group(1)) if m else 1
                return now - timedelta(days=months * 30)
            else:
                # Try absolute date string format
                # e.g., "May 10, 2026" or "10 May 2026"
                clean_date = re.sub(r'\s+ago\s*$', '', date_str)
                clean_date = re.sub(r'^[·\s]+', '', clean_date)
                for fmt in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(clean_date, fmt)
                    except ValueError:
                        continue
        except Exception:
            pass
        return now
