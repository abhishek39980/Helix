import httpx
import logging
import re
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger("helix.knowledge_resolver")

class KnowledgeResolver:
    def __init__(self, opencage_key: str = ""):
        self.opencage_key = opencage_key
        self.timeout = 15.0
        self.headers = {"User-Agent": "Helix-Forensic-Engine/1.0 (contact: forensic-research@pi-labs.org)"}

    async def resolve_wikidata(self, entity: str) -> Optional[Dict[str, Any]]:
        """Queries Wikidata search and claims to resolve country, coordinates, and timezone."""
        logger.info(f"Wikidata lookup: {entity}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 1. Search for entity
                search_url = "https://www.wikidata.org/w/api.php"
                params = {
                    "action": "wbsearchentities",
                    "search": entity,
                    "language": "en",
                    "format": "json"
                }
                resp = await client.get(search_url, params=params, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    search_results = data.get("search", [])
                    if not search_results:
                        return None
                    
                    first_res = search_results[0]
                    qid = first_res.get("id")
                    description = first_res.get("description", "").lower()
                    label = first_res.get("label", "").lower()
                    
                    # Scanning labels/descriptions is highly effective
                    country_guess = None
                    if "japan" in label or "japan" in description:
                        country_guess = "Japan"
                    elif "india" in label or "india" in description:
                        country_guess = "India"
                    elif "united states" in label or "usa" in label or "united states" in description or "usa" in description:
                        country_guess = "United States"
                    elif "united kingdom" in label or "uk" in label or "united kingdom" in description or "uk" in description:
                        country_guess = "United Kingdom"
                        
                    # 2. Fetch claims for QID (P17 is country, P625 is coordinates)
                    get_url = "https://www.wikidata.org/w/api.php"
                    get_params = {
                        "action": "wbgetentities",
                        "ids": qid,
                        "languages": "en",
                        "format": "json"
                    }
                    resp_get = await client.get(get_url, params=get_params, headers=self.headers)
                    if resp_get.status_code == 200:
                        entity_data = resp_get.json().get("entities", {}).get(qid, {})
                        claims = entity_data.get("claims", {})
                        
                        # Fetch P17 (Country)
                        p17_claims = claims.get("P17", [])
                        if p17_claims and not country_guess:
                            # Try to get entity QID of the country
                            country_qid = p17_claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                            if country_qid:
                                # Quick lookup of country QID
                                country_resp = await client.get(get_url, params={"action": "wbgetentities", "ids": country_qid, "languages": "en", "format": "json"}, headers=self.headers)
                                if country_resp.status_code == 200:
                                    country_guess = country_resp.json().get("entities", {}).get(country_qid, {}).get("labels", {}).get("en", {}).get("value")
                        
                        # Fetch P625 (Coordinates)
                        coordinates = []
                        p625_claims = claims.get("P625", [])
                        if p625_claims:
                            val = p625_claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                            lat = val.get("latitude")
                            lon = val.get("longitude")
                            if lat is not None and lon is not None:
                                coordinates = [lat, lon]
                                
                        if country_guess:
                            return {
                                "entity": entity,
                                "country": country_guess,
                                "coordinates": coordinates,
                                "timezone": "", # Will map timezone separately based on country/coordinates
                                "source": "Wikidata"
                            }
        except Exception as e:
            logger.error(f"Wikidata resolution error for {entity}: {e}")
        return None

    async def resolve_openstreetmap(self, entity: str) -> Optional[Dict[str, Any]]:
        """Queries OpenStreetMap Nominatim geocoding API to resolve country & coordinates."""
        logger.info(f"OpenStreetMap Nominatim lookup: {entity}")
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": entity,
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=self.headers)
                if resp.status_code == 200:
                    results = resp.json()
                    if results:
                        res = results[0]
                        address = res.get("address", {})
                        country = address.get("country")
                        lat = float(res.get("lat", 0.0))
                        lon = float(res.get("lon", 0.0))
                        if country:
                            return {
                                "entity": entity,
                                "country": country,
                                "coordinates": [lat, lon],
                                "timezone": "",
                                "source": "OpenStreetMap"
                            }
        except Exception as e:
            logger.error(f"OpenStreetMap Nominatim error for {entity}: {e}")
        return None

    async def resolve_opencage(self, entity: str) -> Optional[Dict[str, Any]]:
        """Queries OpenCage geocoding service (requires API key)."""
        if not self.opencage_key:
            return None
        logger.info(f"OpenCage lookup: {entity}")
        try:
            from backend import _geocode_opencage
            res = _geocode_opencage(entity)
            if res:
                country, state, city, tz_label, offset = res
                return {
                    "entity": entity,
                    "country": country,
                    "coordinates": [], # OpenCage geocode in backend returns country, state, city, tz, offset
                    "timezone": tz_label,
                    "source": "OpenCage"
                }
        except Exception as e:
            logger.error(f"OpenCage error for {entity}: {e}")
        return None

    async def resolve_entity(self, entity: str) -> Optional[Dict[str, Any]]:
        """Runs the resolution pipeline (Wikidata -> OSM -> OpenCage)."""
        clean_entity = entity.strip()
        if not clean_entity:
            return None
            
        # 1. Wikidata
        res = await self.resolve_wikidata(clean_entity)
        if res:
            return res

        # 2. OpenStreetMap/Nominatim
        res = await self.resolve_openstreetmap(clean_entity)
        if res:
            return res

        # 3. OpenCage (if key exists)
        res = await self.resolve_opencage(clean_entity)
        if res:
            return res

        return None
