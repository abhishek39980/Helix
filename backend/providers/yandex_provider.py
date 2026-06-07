import logging
from providers.base_provider import SearchProvider
from providers.serper_provider import SerperProvider

logger = logging.getLogger("helix.providers.yandex")

class YandexProvider(SearchProvider):
    """Yandex Visual search provider wrapper."""

    def __init__(self):
        self.serper = SerperProvider()

    async def search_by_image(self, keyframe_bytes: bytes, filename: str = "") -> list[dict]:
        logger.info("Executing Yandex reverse visual search...")
        matches = await self.serper.search_by_image(keyframe_bytes, filename)
        for m in matches:
            m["platform"] = self.normalize_platform(m["url"])
            m["caption"] = f"[Yandex Match] {m['caption']}"
        return matches

    async def search_by_metadata(self, query: str) -> list[dict]:
        return await self.serper.search_by_metadata(query)
