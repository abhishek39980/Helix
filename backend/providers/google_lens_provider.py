import logging
from providers.base_provider import SearchProvider
from providers.serper_provider import SerperProvider

logger = logging.getLogger("helix.providers.lens")

class GoogleLensProvider(SearchProvider):
    """Google Lens visual search provider wrapper."""

    def __init__(self):
        self.serper = SerperProvider()

    async def search_by_image(self, keyframe_bytes: bytes, filename: str = "") -> list[dict]:
        logger.info("Executing Google Lens reverse visual search...")
        # Resolve via Serper proxy search
        matches = await self.serper.search_by_image(keyframe_bytes, filename)
        for m in matches:
            m["platform"] = self.normalize_platform(m["url"])
            # Enrich caption with Lens detection tag
            m["caption"] = f"[Google Lens Match] {m['caption']}"
        return matches

    async def search_by_metadata(self, query: str) -> list[dict]:
        return await self.serper.search_by_metadata(query)
