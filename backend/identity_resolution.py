import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from evidence import Evidence

logger = logging.getLogger("helix.identity_resolution")

class IdentityResolutionPlugin:
    def __init__(self, platform_name: str, site_domain: str):
        self.platform_name = platform_name
        self.site_domain = site_domain

    def calculate_username_similarity(self, u1: str, u2: str) -> float:
        # Jaro-Winkler similarity algorithm to robustly handle username prefixes/suffixes
        u1_clean = u1.replace("@", "").lower().strip()
        u2_clean = u2.replace("@", "").lower().strip()
        if u1_clean == u2_clean:
            return 1.0
        
        len1, len2 = len(u1_clean), len(u2_clean)
        if len1 == 0 or len2 == 0:
            return 0.0
            
        # Max distance to search for matching characters
        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0
            
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matching characters
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(len2, i + match_distance + 1)
            for j in range(start, end):
                if not s2_matches[j] and u1_clean[i] == u2_clean[j]:
                    s1_matches[i] = True
                    s2_matches[j] = True
                    matches += 1
                    break
                    
        if matches == 0:
            return 0.0
            
        # Find transpositions
        k = 0
        for i in range(len1):
            if s1_matches[i]:
                while not s2_matches[k]:
                    k += 1
                if u1_clean[i] != u2_clean[k]:
                    transpositions += 1
                k += 1
                
        transpositions //= 2
        
        # Jaro similarity
        jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0
        
        # Winkler modification (common prefix boost)
        prefix_len = 0
        for i in range(min(4, len1, len2)):
            if u1_clean[i] == u2_clean[i]:
                prefix_len += 1
            else:
                break
                
        scaling_factor = 0.1
        return jaro + prefix_len * scaling_factor * (1.0 - jaro)

    async def search_platform_profile(self, target_username: str, original_profile: dict) -> Optional[Dict[str, Any]]:
        """Queries Google search via Serper to find profiles on this platform domain."""
        from backend import SERPER_API_KEY, get_async_client
        if not SERPER_API_KEY:
            return None

        clean_username = target_username.replace("@", "").replace("u/", "").strip()
        query = f'site:{self.site_domain} "{clean_username}"'
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": 3}
        
        try:
            client = get_async_client()
            resp = await client.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("organic", [])
                for r in results:
                    link = r.get("link", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    
                    if link and self.site_domain in link.lower():
                        # Validate if link looks like profile URL
                        # Remove trailing slashes and query parameters first
                        url_path = link.rstrip("/").split("?")[0]
                        path_parts = url_path.split("/")
                        parsed_username = path_parts[-1] if path_parts else ""
                        
                        # Handle LinkedIn suffixes: e.g. "kasamacura-phi-studio-764b14386"
                        # Extract suffix base (before first hyphen) if it matches target
                        if "-" in parsed_username:
                            prefix = parsed_username.split("-")[0]
                            if prefix.lower() == clean_username.lower():
                                parsed_username = prefix
                                
                        similarity = self.calculate_username_similarity(clean_username, parsed_username)
                        if similarity >= 0.75 or clean_username.lower() in parsed_username.lower():
                            final_similarity = max(similarity, 0.85 if clean_username.lower() in parsed_username.lower() else 0.0)
                            
                            # Parse location from snippet if possible
                            location = ""
                            loc_m = re.search(r"(?:location|based in|📍)[:\s]*([a-zA-Z\s,]{3,25})", snippet, re.IGNORECASE)
                            if loc_m:
                                location = loc_m.group(1).strip()
                            
                            return {
                                "platform": self.platform_name,
                                "username": parsed_username,
                                "url": link,
                                "display_name": title,
                                "bio": snippet,
                                "location": location,
                                "similarity": final_similarity
                            }
        except Exception as e:
            logger.error(f"Failed identity search for {self.platform_name}: {e}")
        return None


class IdentityResolutionEngine:
    def __init__(self):
        self.plugins: List[IdentityResolutionPlugin] = []
        self.register_default_plugins()

    def register_default_plugins(self):
        self.plugins.append(IdentityResolutionPlugin("GitHub", "github.com"))
        self.plugins.append(IdentityResolutionPlugin("LinkedIn", "linkedin.com"))
        self.plugins.append(IdentityResolutionPlugin("Reddit", "reddit.com/user"))
        self.plugins.append(IdentityResolutionPlugin("Telegram", "t.me"))
        self.plugins.append(IdentityResolutionPlugin("TikTok", "tiktok.com/@"))
        self.plugins.append(IdentityResolutionPlugin("Instagram", "instagram.com"))
        self.plugins.append(IdentityResolutionPlugin("Bluesky", "bsky.app/profile"))
        self.plugins.append(IdentityResolutionPlugin("Mastodon", "mastodon.social/@"))

    async def resolve_identity(self, username: str, original_profile: dict, session_id: str) -> List[Evidence]:
        """Resolves identity across registered platforms and returns corroborating Evidence."""
        evidence_list = []
        
        for plugin in self.plugins:
            res = await plugin.search_platform_profile(username, original_profile)
            if res:
                logger.info(f"Cross-Platform Match: Found {res['platform']} profile '{res['username']}' (Similarity: {res['similarity'] * 100:.1f}%)")
                
                # Check for location evidence inside this platform match
                location = res.get("location", "")
                
                ev = Evidence(
                    source=f"identity_resolution_{plugin.platform_name.lower()}",
                    source_type="cross_platform_match",
                    collection_method="serp_identity_discovery",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    reliability=res["similarity"] * 0.85, # Scale reliability based on username similarity
                    value={
                        "platform": res["platform"],
                        "url": res["url"],
                        "username": res["username"],
                        "location": location,
                        "bio": res["bio"]
                    },
                    metadata={
                        "session_id": session_id,
                        "similarity_score": res["similarity"]
                    }
                )
                evidence_list.append(ev)
                
        return evidence_list
