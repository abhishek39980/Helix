import re
import logging
from PIL import Image, ImageDraw
import io
import shutil
import asyncio

logger = logging.getLogger("helix.ocr_manager")

class OCRManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OCRManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, strict_mode: bool = True):
        if self._initialized:
            return
        self.strict_mode = strict_mode
        self._paddle_ocr = None
        self._easyocr_reader = None
        self._tesseract_available = None
        self._loaded = False
        self._initialized = True

    def _ensure_loaded(self):
        """Lazy loader for the OCR engines to prevent repeated imports and heavy loads during module imports."""
        if self._loaded:
            return
        
        # 1. PaddleOCR Disabled 
        # Disabled to prevent the pir::ArrayAttribute C++ crash on Windows.
        self._paddle_ocr = None
        logger.info("PaddleOCR manually disabled. Bypassing straight to EasyOCR.")

        

        # 2. Detect and load EasyOCR
        if not self._paddle_ocr:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(['en', 'ja'])
                logger.info("EasyOCR successfully loaded.")
            except Exception as e:
                logger.info(f"EasyOCR not loaded / not available: {e}")

        # 3. Detect Tesseract
        self._tesseract_available = shutil.which("tesseract") is not None
        if self._tesseract_available:
            logger.info("Tesseract CLI successfully detected.")

        self._loaded = True

    async def log_audit_event(self, action: str, details: str):
        """Writes audit trail records to the database."""
        try:
            from db import AuditLog, async_session
            async with async_session() as session:
                session.add(AuditLog(action=action, details=details))
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to write OCR audit log: {e}")

    async def perform_startup_validation(self) -> bool:
        """
        Validates the OCR setup by running an in-memory mock OCR test on startup.
        Logs versioning information and supported OCR methods.
        """
        try:
            self._ensure_loaded()
            
            # Create a tiny 20x20 in-memory validation PNG image with some black lines
            img = Image.new('RGB', (40, 40), color='white')
            draw = ImageDraw.Draw(img)
            draw.line([(0, 0), (40, 40)], fill='black')
            draw.line([(0, 40), (40, 0)], fill='black')
            
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            test_bytes = buf.getvalue()

            # Execute OCR dry run
            res = self.run_ocr(test_bytes, "startup_validation_dummy.png")
            
            # Determine OCR Version & Methods
            ocr_version = "Unknown"
            methods = []
            if self._paddle_ocr:
                try:
                    import paddleocr
                    ocr_version = f"PaddleOCR v{getattr(paddleocr, '__version__', 'unknown')}"
                except Exception:
                    ocr_version = "PaddleOCR"
                methods.append("paddleocr")
            elif self._easyocr_reader:
                try:
                    import easyocr
                    ocr_version = f"EasyOCR v{getattr(easyocr, '__version__', 'unknown')}"
                except Exception:
                    ocr_version = "EasyOCR"
                methods.append("easyocr")
            
            if self._tesseract_available:
                methods.append("tesseract")

            log_details = f"Validation completed. Active engine: {ocr_version}. Supported methods: {methods}. Status: {res.get('status')}"
            logger.info(f"OCR Startup Validation: {log_details}")
            await self.log_audit_event("ocr_initialized", log_details)
            return True
        except Exception as e:
            err_msg = f"OCR Startup Validation failed: {e}"
            logger.error(err_msg)
            await self.log_audit_event("ocr_failed", err_msg)
            return False

    def run_paddle_ocr(self, image_bytes: bytes) -> str:
        if not self._paddle_ocr:
            raise ImportError("PaddleOCR not initialized.")
        
        # Safe decoding of raw bytes to BGR numpy array as required by PaddleOCR
        import numpy as np
        import cv2
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img_np = np.array(img)
            if len(img_np.shape) == 3 and img_np.shape[2] == 3:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        except Exception as decode_err:
            logger.error(f"PaddleOCR BGR decoding failed: {decode_err}")
            raise decode_err

        # Version-safe call logic: catch TypeError to handle parameter signature mismatches
        try:
            result = self._paddle_ocr.ocr(img_np, cls=True)
        except TypeError as te:
            logger.warning(f"PaddleOCR prediction failed with parameter TypeError: {te}. Retrying without 'cls' argument.")
            result = self._paddle_ocr.ocr(img_np)
        except Exception as e:
            logger.error(f"PaddleOCR execution failed: {e}")
            raise e

        texts = []
        if result and isinstance(result, list):
            for line in result:
                if line:
                    for res in line:
                        texts.append(res[1][0])
        return " ".join(texts)

    def run_easyocr(self, image_bytes: bytes) -> str:
        if not self._easyocr_reader:
            raise ImportError("EasyOCR not initialized.")
        
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes))
        img_np = np.array(img)
        result = self._easyocr_reader.readtext(img_np)
        texts = [res[1] for res in result]
        return " ".join(texts)

    def run_tesseract(self, image_bytes: bytes) -> str:
        if not self._tesseract_available:
            raise ImportError("Tesseract binary not available.")
        
        try:
            import pytesseract
            img = Image.open(io.BytesIO(image_bytes))
            return pytesseract.image_to_string(img)
        except Exception:
            # Fallback to direct subprocess
            import tempfile
            import subprocess
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            
            out_txt_base = tmp_path + "_out"
            try:
                cmd = ["tesseract", tmp_path, out_txt_base]
                result = subprocess.run(cmd, capture_output=True, timeout=15)
                if result.returncode == 0:
                    txt_path = out_txt_base + ".txt"
                    if os.path.exists(txt_path):
                        with open(txt_path, "r", encoding="utf-8") as f:
                            text = f.read()
                        try:
                            os.remove(txt_path)
                        except Exception:
                            pass
                        return text
            except Exception as e:
                logger.error(f"Tesseract subprocess failed: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        raise RuntimeError("Tesseract execution failed.")

    def run_ocr(self, image_bytes: bytes, filename: str = "") -> dict:
        """Runs the OCR pipeline and extracts metadata patterns and logos with dynamic fallbacks."""
        self._ensure_loaded()
        ocr_text = ""
        provider_used = "none"
        confidence = 0.0

        # 1. Try PaddleOCR
        if self._paddle_ocr:
            try:
                ocr_text = self.run_paddle_ocr(image_bytes)
                provider_used = "paddleocr"
                confidence = 0.90
            except Exception as e:
                logger.error(f"PaddleOCR execution failed, falling back to EasyOCR: {e}")

        # 2. Try EasyOCR
        if not ocr_text and self._easyocr_reader:
            try:
                ocr_text = self.run_easyocr(image_bytes)
                provider_used = "easyocr"
                confidence = 0.85
            except Exception as e:
                logger.error(f"EasyOCR execution failed, falling back to Tesseract: {e}")

        # 3. Try Tesseract
        if not ocr_text and self._tesseract_available:
            try:
                ocr_text = self.run_tesseract(image_bytes)
                provider_used = "tesseract"
                confidence = 0.70
            except Exception as e:
                logger.error(f"Tesseract execution failed: {e}")

        # Return empty envelope if all failed (never crash or throw)
        if not ocr_text:
            return {
                "status": "unavailable",
                "reason": "ocr_unavailable",
                "text": "",
                "features": {
                    "usernames": [], "urls": [], "hashtags": [],
                    "domains": [], "phone_numbers": [], "locations": []
                },
                "logos": [],
                "provider": "none",
                "confidence": 0.0
            }

        # Clean text
        ocr_text = ocr_text.strip()
        
        # Extract features and logos
        from ocr_intelligence import extract_metadata_patterns, detect_logos_and_watermarks
        features = extract_metadata_patterns(ocr_text)
        logos = detect_logos_and_watermarks(ocr_text)

        return {
            "status": "success",
            "text": ocr_text,
            "features": features,
            "logos": logos,
            "provider": provider_used,
            "confidence": confidence
        }
