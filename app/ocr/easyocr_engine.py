"""
Invoice OCR Processing System - EasyOCR Engine Implementation
Wraps EasyOCR library with lazy initialization and word confidence extraction.
"""

import time
from pathlib import Path
from typing import Tuple, Optional
from app.ocr.base import BaseOCREngine, OCRResult, OCRWordBox

class EasyOCREngine(BaseOCREngine):
    """EasyOCR Engine implementation."""

    def __init__(self):
        self._reader = None
        super().__init__("EasyOCR")

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Verifies if EasyOCR and PyTorch dependencies can be imported."""
        try:
            import easyocr
            import torch
            return True, None
        except ImportError as e:
            return False, f"EasyOCR or PyTorch dependency missing: {str(e)}"
        except Exception as e:
            return False, f"EasyOCR initialization check error: {str(e)}"

    def _get_reader(self):
        if self._reader is None and self.available:
            import easyocr
            # Lazy initialize English reader (gpu=False for CPU local fallback compatibility)
            self._reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        return self._reader

    def process_image(self, image_path: Path) -> OCRResult:
        if not self.available:
            return OCRResult(
                engine_name=self.name,
                full_text="",
                confidence=0.0,
                is_available=False,
                error_message=self.init_error
            )

        start_time = time.time()
        try:
            reader = self._get_reader()
            if reader is None:
                raise RuntimeError("Failed to load EasyOCR reader instance.")

            # readtext returns: [ (bbox, text, prob), ... ]
            results = reader.readtext(str(image_path))

            words = []
            text_lines = []
            confidences = []

            for bbox, text, prob in results:
                conf = float(prob) * 100.0
                confidences.append(conf)
                text_lines.append(text)
                
                # Convert polygon bbox to bounding box coords
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                words.append(OCRWordBox(
                    text=text,
                    confidence=round(conf, 2),
                    bbox=[min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                ))

            full_text = "\n".join(text_lines)
            avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
            exec_time = (time.time() - start_time) * 1000.0

            return OCRResult(
                engine_name=self.name,
                full_text=full_text,
                confidence=round(avg_conf, 2),
                words=words,
                execution_time_ms=round(exec_time, 2)
            )

        except Exception as e:
            exec_time = (time.time() - start_time) * 1000.0
            return OCRResult(
                engine_name=self.name,
                full_text="",
                confidence=0.0,
                execution_time_ms=round(exec_time, 2),
                error_message=f"EasyOCR processing error: {str(e)}"
            )
