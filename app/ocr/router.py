"""
Invoice OCR Processing System - OCR Router Module
Dynamically ranks available OCR engines based on document characteristics,
image metrics, layout structure, and configurable engine weights.
"""

from typing import List, Dict, Any, Tuple
import config
from app.ocr.base import BaseOCREngine
from app.ocr.tesseract_engine import TesseractOCREngine
from app.ocr.easyocr_engine import EasyOCREngine
from app.ocr.surya_engine import SuryaOCREngine
from app.ocr.doctr_engine import DocTROCREngine
from app.ocr.paddleocr_engine import PaddleOCREngine

class OCRRouter:
    """Orchestrates dynamic engine scoring and fallback routing."""

    def __init__(self):
        # Register all available engine plugin instances
        self.engines: Dict[str, BaseOCREngine] = {
            "PaddleOCR": PaddleOCREngine(),
            "Surya": SuryaOCREngine(),
            "Tesseract": TesseractOCREngine(),
            "docTR": DocTROCREngine(),
            "EasyOCR": EasyOCREngine()
        }

    def get_ranked_engines(self, doc_inspection: Dict[str, Any], doc_analysis: Dict[str, Any]) -> List[Tuple[BaseOCREngine, float, str]]:
        """
        Calculates suitability score for each engine based on document inspection & analysis metrics.
        Returns list of (engine_instance, score, rationale) sorted by score descending.
        """
        doc_type = doc_inspection.get("document_type", "Scanned PDF")
        is_digital = doc_type == "Digital PDF"
        has_tables = doc_analysis.get("has_tables", False)
        is_noisy = doc_analysis.get("is_noisy", False)
        is_low_contrast = doc_analysis.get("is_low_contrast", False)
        skew_angle = abs(doc_analysis.get("skew_angle", 0.0))

        ranked_list = []

        for name, engine in self.engines.items():
            engine_cfg = config.OCR_ENGINE_CONFIG.get(name, {})
            if not engine_cfg.get("enabled", True):
                continue

            base_priority = engine_cfg.get("priority", 10)
            
            # Base weight by document mode
            if is_digital:
                score = engine_cfg.get("weight_digital", 0.80) * 100.0
            else:
                score = engine_cfg.get("weight_scanned", 0.80) * 100.0

            rationales = []

            # Adjust score by specific document characteristics
            if is_digital and name == "Tesseract":
                score += 10.0
                rationales.append("Digital text stream favor Tesseract fast parsing")

            if has_tables and name in ["PaddleOCR", "Surya"]:
                score += 15.0
                rationales.append("Table structure detected favor layout-aware engines")

            if (is_noisy or is_low_contrast) and name in ["EasyOCR", "docTR"]:
                score += 10.0
                rationales.append("Noisy image favors robust deep-learning OCR")

            if skew_angle > 5.0 and name in ["PaddleOCR", "Surya"]:
                score += 8.0
                rationales.append("Significant skew angle favors angle-classified OCR")

            # Penalize unavailable engines so they fall to bottom with clear explanation
            if not engine.available:
                score = -100.0
                rationales.append(f"UNAVAILABLE: {engine.init_error}")

            rationales_str = "; ".join(rationales) if rationales else "Standard capability match"
            ranked_list.append((engine, score, rationales_str))

        # Sort descending by score
        ranked_list.sort(key=lambda x: x[1], reverse=True)
        return ranked_list
