"""
Invoice OCR Processing System - PaddleOCR Engine Implementation
Wraps PaddleOCR for multi-lingual document and table text extraction.
"""

import time
from pathlib import Path
from typing import Tuple, Optional
from app.ocr.base import BaseOCREngine, OCRResult, OCRWordBox

class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR Engine implementation."""

    def __init__(self):
        self._ocr = None
        super().__init__("PaddleOCR")

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Verifies if paddleocr is installed."""
        try:
            import paddleocr
            return True, None
        except ImportError as e:
            return False, f"PaddleOCR dependency missing: {str(e)}"
        except Exception as e:
            return False, f"PaddleOCR availability check error: {str(e)}"


    def _get_ocr(self):
        if self._ocr is None and self.available:
            from paddleocr import PaddleOCR
            try:
                self._ocr = PaddleOCR(use_textline_orientation=True, lang='en', show_log=False)
            except (TypeError, ValueError):
                self._ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        return self._ocr

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
            ocr = self._get_ocr()
            result = ocr.ocr(str(image_path), cls=True)

            words = []
            text_lines = []
            confidences = []

            if result and len(result) > 0 and result[0] is not None:
                for line in result[0]:
                    # line format: [ [ [x1,y1],[x2,y2],[x3,y3],[x4,y4] ], (text, confidence) ]
                    box, (txt, conf) = line
                    conf_pct = float(conf) * 100.0
                    confidences.append(conf_pct)
                    text_lines.append(txt)

                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]

                    words.append(OCRWordBox(
                        text=txt,
                        confidence=round(conf_pct, 2),
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
                error_message=f"PaddleOCR processing error: {str(e)}"
            )
