"""
Invoice OCR Processing System - docTR OCR Engine Implementation
Wraps docTR (Mindee OCR) library for document parsing.
"""

import time
from pathlib import Path
from typing import Tuple, Optional
from app.ocr.base import BaseOCREngine, OCRResult, OCRWordBox

class DocTROCREngine(BaseOCREngine):
    """docTR (Mindee Document OCR) Engine implementation."""

    def __init__(self):
        self._predictor = None
        super().__init__("docTR")

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Verifies if docTR (python-doctr) is installed."""
        try:
            import doctr
            import doctr.models
            import doctr.io
            return True, None
        except ImportError as e:
            return False, f"docTR (python-doctr) dependency missing: {str(e)}"
        except Exception as e:
            return False, f"docTR check error: {str(e)}"

    def _get_predictor(self):
        if self._predictor is None and self.available:
            from doctr.models import ocr_predictor
            # Initialize lightweight pretrained model
            self._predictor = ocr_predictor(pretrained=True)
        return self._predictor

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
            from doctr.io import DocumentFile
            predictor = self._get_predictor()

            doc = DocumentFile.from_images(str(image_path))
            result = predictor(doc)

            words = []
            text_lines = []
            confidences = []

            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        line_words = []
                        for word in line.words:
                            txt = word.value
                            conf = float(word.confidence) * 100.0
                            confidences.append(conf)
                            line_words.append(txt)
                            words.append(OCRWordBox(
                                text=txt,
                                confidence=round(conf, 2),
                                bbox=[
                                    float(word.geometry[0][0]),
                                    float(word.geometry[0][1]),
                                    float(word.geometry[1][0]),
                                    float(word.geometry[1][1])
                                ]
                            ))
                        if line_words:
                            text_lines.append(" ".join(line_words))

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
                error_message=f"docTR processing error: {str(e)}"
            )
