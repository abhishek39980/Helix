import re
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional
from provider_health import health_registry

logger = logging.getLogger("helix.profile_collection")

@dataclass
class ActualPost:
    full_text: str
    created_at: str         # Real posting timestamp (ISO string or standard UTC string)
    hashtags: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    post_id: str = ""
    username: str = ""
    platform: str = ""

@dataclass
class SearchMention:
    full_text: str
    created_at: str         # Index timestamp or snippet date (Google search timestamp)
    hashtags: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    source_url: str = ""
    username: str = ""
    platform: str = ""


class ProfileCollectionPipeline:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    async def fetch_nitter(self, username: str) -> Optional[Tuple[dict, List[ActualPost]]]:
        t0 = time.time()
        try:
            from backend import fetch_via_nitter
            profile, tweets = await fetch_via_nitter(username)
            if tweets:
                posts = [
                    ActualPost(
                        full_text=t["full_text"],
                        created_at=t["created_at"],
                        hashtags=[h["text"] for h in t.get("hashtags", [])],
                        urls=t.get("urls", []),
                        post_id=t.get("tweet_id", ""),
                        username=username,
                        platform="X (Twitter)"
                    )
                    for t in tweets
                ]
                health_registry.record_success("profile", "Nitter", time.time() - t0)
                return profile, posts
        except Exception as e:
            logger.error(f"Nitter fetch error: {e}")
        health_registry.record_failure("profile", "Nitter")
        return None

    async def fetch_scrapebadger(self, username: str) -> Optional[Tuple[dict, List[ActualPost]]]:
        t0 = time.time()
        try:
            from backend import fetch_profile_scrapebadger
            sb_profile = await fetch_profile_scrapebadger(username)
            if sb_profile and sb_profile.get("status") != "error":
                profile = {
                    "display_name": sb_profile.get("display_name", ""),
                    "description": sb_profile.get("description", ""),
                    "location": sb_profile.get("location", ""),
                    "website": sb_profile.get("website", ""),
                    "join_date": sb_profile.get("join_date", "")
                }
                # ScrapeBadger doesn't return posts in our current configuration, only profile metadata
                health_registry.record_success("profile", "ScrapeBadger", time.time() - t0)
                return profile, []
        except Exception as e:
            logger.error(f"ScrapeBadger fetch error: {e}")
        health_registry.record_failure("profile", "ScrapeBadger")
        return None

    async def fetch_serp(self, username: str) -> Optional[Tuple[dict, List[SearchMention]]]:
        t0 = time.time()
        try:
            from backend import fetch_twitter_profile_serp, fetch_twitter_tweets_serp_fallback
            profile = await fetch_twitter_profile_serp(username)
            tweets = await fetch_twitter_tweets_serp_fallback(username)
            
            mentions = [
                SearchMention(
                    full_text=t["full_text"],
                    created_at=t["created_at"], # date indexed by Google
                    hashtags=[h["text"] for h in t.get("hashtags", [])],
                    urls=t.get("urls", []),
                    source_url=t.get("url", ""),
                    username=username,
                    platform="X (Twitter)"
                )
                for t in tweets
            ]
            health_registry.record_success("profile", "SERP", time.time() - t0)
            return profile, mentions
        except Exception as e:
            logger.error(f"SERP fetch error: {e}")
        health_registry.record_failure("profile", "SERP")
        return None

    async def collect_twitter_profile(self, username: str) -> Tuple[dict, List[Any], str]:
        """Runs the collection priority chain for Twitter/X profiles."""
        clean = username.strip("@").lower()
        
        # Priority order: Official API (not implemented/skipped) -> Direct Scrapers -> ScrapeBadger -> SERP Discovery -> Nitter
        # Wait, the mandate says: Nitter is low-priority fallback.
        # Let's run in prioritized order:
        
        # 1. ScrapeBadger profile lookup
        sb_res = await self.fetch_scrapebadger(clean)
        if sb_res:
            profile, posts = sb_res
            # If we got profile but no posts, try to enrich posts via Nitter
            nitter_res = await self.fetch_nitter(clean)
            if nitter_res:
                n_profile, n_posts = nitter_res
                posts.extend(n_posts)
                if n_profile.get("location") and not profile.get("location"):
                    profile["location"] = n_profile["location"]
            # If still no posts, enrich mentions via SERP
            if not posts:
                serp_res = await self.fetch_serp(clean)
                if serp_res:
                    s_profile, s_mentions = serp_res
                    posts.extend(s_mentions)
            return profile, posts, "scrapebadger"

        # 2. Nitter lookup
        nitter_res = await self.fetch_nitter(clean)
        if nitter_res:
            profile, posts = nitter_res
            return profile, posts, "nitter"

        # 3. SERP lookup (only SearchMentions)
        serp_res = await self.fetch_serp(clean)
        if serp_res:
            profile, mentions = serp_res
            return profile, mentions, "serp"

        # If everything fails
        if self.strict_mode:
            raise ValueError("profile_collection_failed")
            
        return {}, [], "failed"
