"""
Invoice OCR Processing System - Surya OCR Engine Implementation
Wraps Surya OCR library for layout-aware document text extraction.
"""

import time
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from app.ocr.base import BaseOCREngine, OCRResult, OCRWordBox

class SuryaOCREngine(BaseOCREngine):
    """Surya OCR Engine wrapper."""

    def __init__(self):
        self._langs = ["en"]
        self._rec_predictor = None
        self._det_predictor = None
        super().__init__("Surya")

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Verifies if Surya OCR module is installed and available."""
        try:
            import surya
            try:
                from surya.recognition import RecognitionPredictor
                return True, None
            except ImportError:
                import surya.ocr
                return True, None
        except ImportError as e:
            return False, f"Surya OCR library dependency missing: {str(e)}"
        except Exception as e:
            return False, f"Surya OCR availability check error: {str(e)}"

    def _load_models(self):
        if self._rec_predictor is None and self.available:
            try:
                from surya.recognition import RecognitionPredictor
                from surya.detection import DetectionPredictor
                self._rec_predictor = RecognitionPredictor()
                self._det_predictor = DetectionPredictor()
            except ImportError:
                from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
                from surya.model.recognition.model import load_model as load_rec_model
                from surya.model.recognition.processor import load_processor as load_rec_processor

                self._det_processor = load_det_processor()
                self._det_model = load_det_model()
                self._rec_model = load_rec_model()
                self._rec_processor = load_rec_processor()

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
            img = Image.open(image_path).convert("RGB")
            self._load_models()

            words = []
            lines = []
            confidences = []

            # Modern Surya 0.20+ Predictor API
            if self._rec_predictor is not None:
                predictions = self._rec_predictor([img], [self._langs], det_predictor=self._det_predictor)
                if predictions and len(predictions) > 0:
                    page_pred = predictions[0]
                    for text_line in getattr(page_pred, 'text_lines', []):
                        txt = getattr(text_line, 'text', '').strip()
                        if not txt:
                            continue
                        conf = float(getattr(text_line, 'confidence', 0.85)) * 100.0
                        confidences.append(conf)
                        lines.append(txt)
                        bbox = getattr(text_line, 'bbox', None)

                        words.append(OCRWordBox(
                            text=txt,
                            confidence=round(conf, 2),
                            bbox=bbox
                        ))
            else:
                # Legacy Surya API
                from surya.ocr import run_ocr
                predictions = run_ocr(
                    [img],
                    [self._langs],
                    self._det_model,
                    self._det_processor,
                    self._rec_model,
                    self._rec_processor
                )
                if predictions and len(predictions) > 0:
                    page_pred = predictions[0]
                    for text_line in getattr(page_pred, 'text_lines', []):
                        txt = text_line.text.strip()
                        conf = float(getattr(text_line, 'confidence', 0.85)) * 100.0
                        confidences.append(conf)
                        lines.append(txt)
                        bbox = getattr(text_line, 'bbox', None)

                        words.append(OCRWordBox(
                            text=txt,
                            confidence=round(conf, 2),
                            bbox=bbox
                        ))

            full_text = "\n".join(lines)
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
                error_message=f"Surya OCR processing error: {str(e)}"
            )

