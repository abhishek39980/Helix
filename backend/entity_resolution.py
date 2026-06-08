import logging
import re
from typing import List, Dict, Any, Optional
from knowledge_resolver import KnowledgeResolver
from evidence import Evidence
from datetime import datetime, timezone

logger = logging.getLogger("helix.entity_resolution")

def is_valid_location_entity(text: str, label_type: str = "LOC") -> bool:
    """
    Classifies named entities, allowing only location-relevant types and rejecting
    URLs, domains, programming languages, documentation pages, generic nouns,
    software names, help pages, and technical terminology.
    """
    if not text:
        return False
        
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # 1. Reject empty, too short, or overly long strings
    if len(text_clean) < 3 or len(text_clean) > 100:
        return False
        
    # 2. Reject URLs, domains, email addresses, and filenames
    url_pattern = r'(https?://|www\.)\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b|@\S+'
    if re.search(url_pattern, text_lower) or text_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov', '.mkv', '.pdf', '.csv', '.txt', '.py', '.js', '.html', '.css')):
        return False
        
    # 3. Reject technical terminology, software names, and web GUI pages
    rejected_terms = [
        "javascript", "python", "html", "css", "docker", "kubernetes", "react", "vue", "angular",
        "api", "database", "query", "sql", "git", "github", "gitlab", "npm", "pip", "package",
        "help center", "documentation", "settings", "terms of service", "privacy policy", "log in", "login",
        "sign up", "download", "install", "error", "warning", "exception", "cookie", "cookies", "cache",
        "browser", "click here", "read more", "search", "submit", "cancel", "save", "delete", "edit",
        "username", "password", "email", "address bar", "index", "home", "about us", "contact us", "faq",
        "support", "admin", "dashboard", "console", "terminal", "system", "version", "x.com", "twitter.com",
        "facebook.com", "google.com", "youtube.com", "instagram.com", "linkedin.com", "github.com", "chrome",
        "safari", "firefox", "edge", "opera", "app", "application", "file", "folder", "directory", "host"
    ]
    if any(term in text_lower for term in rejected_terms):
        return False
        
    # 4. Filter by allowed entity labels
    allowed_types = ["GPE", "LOC", "FAC", "LANDMARK", "MONUMENT", "BUILDING", "CITY", "REGION", "COUNTRY", "TOURIST_ATTRACTION"]
    if label_type not in allowed_types:
        return False
        
    # 5. Reject common generic nouns / single words representing actions or generic interface text
    common_interface_nouns = ["close", "open", "menu", "share", "view", "posts", "tweets", "likes", "followers", "following", "reply", "retweet", "media"]
    if text_lower in common_interface_nouns:
        return False
        
    return True

class EntityResolutionEngine:
    def __init__(self, resolver: KnowledgeResolver):
        self.resolver = resolver

    async def log_audit_event(self, action: str, details: str):
        """Helper to write audit events to the database."""
        try:
            from db import AuditLog, async_session
            async with async_session() as session:
                session.add(AuditLog(action=action, details=details))
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to write entity resolution audit log: {e}")

    def extract_ner_entities(self, text: str) -> List[str]:
        """Extracts location-based named entities from text using spaCy NER with classification checks."""
        entities = []
        if not text:
            return entities
            
        # Support Japanese script location names by mapping them to geocoding candidates
        if "東京" in text:
            entities.append("Tokyo")
        if "日本" in text:
            entities.append("Japan")
        if "京都" in text:
            entities.append("Kyoto")
        if "大阪" in text:
            entities.append("Osaka")
        if "江戸前" in text:
            entities.append("Edomae")

        from backend import _get_nlp
        nlp = _get_nlp()
        if not nlp:
            logger.warning("spaCy NLP model not available. Skipping NER extraction.")
            return entities

        doc = nlp(text[:5000])
        for ent in doc.ents:
            val = ent.text.strip()
            # Map ORG (e.g. transit line, railway company) to FAC (Facility) for validation checks
            label = ent.label_
            if label == "ORG":
                label = "FAC"
                
            if label in ("GPE", "LOC", "FAC"):
                if is_valid_location_entity(val, label):
                    if val not in entities:
                        entities.append(val)
        return entities

    async def resolve_text_entities(self, text: str, source_name: str, session_id: str) -> List[Evidence]:
        """Runs NER, queries KnowledgeResolver for each entity, and constructs Evidence artifacts."""
        entities = self.extract_ner_entities(text)
        evidence_list = []
        
        for entity in entities:
            # Classification filtering check
            if not is_valid_location_entity(entity, "LOC"):
                logger.info(f"Entity resolution classification rejected candidate: '{entity}'")
                await self.log_audit_event("entity_rejected", f"Entity rejected (classification filter): '{entity}' (source={source_name})")
                continue

            # Check cache or call resolver
            res = await self.resolver.resolve_entity(entity)
            if res and res.get("country"):
                country = res["country"]
                source = res["source"]
                coords = res.get("coordinates", [])
                
                logger.info(f"Resolved entity '{entity}' -> country '{country}' via {source}")
                await self.log_audit_event("entity_resolved", f"Resolved entity '{entity}' -> {country} via {source}")
                
                # Construct Evidence
                ev = Evidence(
                    source=source,
                    source_type="ner_entity",
                    collection_method="api_query",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    reliability=0.75 if source != "OpenStreetMap" else 0.80,
                    value={
                        "entity": entity,
                        "country": country,
                        "coordinates": coords
                    },
                    metadata={
                        "session_id": session_id,
                        "source_name": source_name
                    }
                )
                evidence_list.append(ev)
            else:
                await self.log_audit_event("entity_rejected", f"Entity resolution failed (resolver lookup failed): '{entity}'")
                
        return evidence_list
