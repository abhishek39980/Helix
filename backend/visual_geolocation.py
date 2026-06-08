import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ocr_manager import OCRManager
from knowledge_resolver import KnowledgeResolver
from entity_resolution import EntityResolutionEngine
from evidence import Evidence

logger = logging.getLogger("helix.visual_geolocation")

class VisualGeolocationEngine:
    def __init__(self, ocr_manager: OCRManager, resolver: KnowledgeResolver, ner_engine: EntityResolutionEngine):
        self.ocr_manager = ocr_manager
        self.resolver = resolver
        self.ner_engine = ner_engine

    async def geolocate_keyframe(self, keyframe_bytes: bytes, filename: str, session_id: str) -> List[Evidence]:
        """Performs independent visual analysis on a keyframe: OCR + NER entity resolution + logo/signage checking."""
        evidence_list = []
        
        # 1. OCR Extraction
        ocr_res = self.ocr_manager.run_ocr(keyframe_bytes, filename)
        if ocr_res.get("status") == "success" and ocr_res.get("text"):
            ocr_text = ocr_res["text"]
            logger.info(f"Visual geolocation extracted OCR: {ocr_text}")
            
            # Record OCR Evidence
            evidence_list.append(Evidence(
                source=ocr_res.get("provider", "local_ocr"),
                source_type="ocr_text",
                collection_method="frame_ocr",
                timestamp=datetime.now(timezone.utc).isoformat(),
                reliability=ocr_res.get("confidence", 0.70),
                value={"text": ocr_text},
                metadata={"session_id": session_id}
            ))

            # 2. Entity Resolution on the OCR text
            ner_evidence = await self.ner_engine.resolve_text_entities(ocr_text, "keyframe_ocr", session_id)
            evidence_list.extend(ner_evidence)

            # 3. Logo/brand signals check
            logos = ocr_res.get("logos", [])
            for logo in logos:
                logo_name = logo.get("logo")
                logo_conf = logo.get("confidence", 0.80)
                
                # Try geolocating brand name (e.g. JR East -> East Japan Railway -> Japan)
                res = await self.resolver.resolve_entity(logo_name)
                if res and res.get("country"):
                    evidence_list.append(Evidence(
                        source="brand_resolver",
                        source_type="brand_signature",
                        collection_method="logo_ocr_resolution",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        reliability=logo_conf,
                        value={
                            "logo": logo_name,
                            "country": res["country"]
                        },
                        metadata={
                            "session_id": session_id,
                            "source_meta": "brand_watermark_match"
                        }
                    ))
                    
        return evidence_list
