"""
Invoice OCR Processing System - OCR Quality Evaluator Module
Calculates a multi-signal composite quality score (0 - 100%) for an OCR result:
1. Raw OCR confidence
2. Dictionary word validity & garbage/noise ratio
3. Critical invoice field signals (GSTIN, Invoice Date, Amounts, Tax keywords)
4. Text length & completeness
"""

import re
from typing import Dict, Any, Tuple
import config
from app.ocr.base import OCRResult

class OCREvaluator:
    """Evaluates quality and accuracy of raw OCR results using multiple heuristic signals."""

    @classmethod
    def evaluate(cls, ocr_result: OCRResult) -> Tuple[float, Dict[str, Any], bool]:
        """
        Evaluates OCR result quality.
        Returns: (quality_score, breakdown_dict, passes_threshold)
        """
        text = ocr_result.full_text.strip()
        if not text:
            return 0.0, {"reason": "Empty OCR output text"}, False

        # 1. Base OCR confidence score (0-100)
        base_confidence_score = ocr_result.confidence

        # 2. Field Signal Detection (GSTIN hit, Date hit, Amount hit, Keywords hit)
        field_signals_score, field_matches = cls._evaluate_field_signals(text)

        # 3. Word Quality & Noise Ratio
        word_quality_score, noise_ratio = cls._evaluate_word_quality(text)

        # 4. Text Completeness score
        text_len = len(text)
        completeness_score = min(100.0, (text_len / 300.0) * 100.0)

        # Weighted composite calculation
        # Weights: Confidence 30%, Field Signals 40%, Word Quality 20%, Completeness 10%
        quality_score = (
            (base_confidence_score * 0.30) +
            (field_signals_score * 0.40) +
            (word_quality_score * 0.20) +
            (completeness_score * 0.10)
        )

        quality_score = round(min(100.0, max(0.0, quality_score)), 2)

        breakdown = {
            "base_confidence_score": round(base_confidence_score, 2),
            "field_signals_score": round(field_signals_score, 2),
            "word_quality_score": round(word_quality_score, 2),
            "completeness_score": round(completeness_score, 2),
            "noise_ratio": round(noise_ratio, 2),
            "detected_field_signals": field_matches
        }

        passes = quality_score >= config.OCR_ACCEPT_THRESHOLD
        return quality_score, breakdown, passes

    @staticmethod
    def _evaluate_field_signals(text: str) -> Tuple[float, Dict[str, bool]]:
        """Scans for key invoice structural indicators."""
        matches = {
            "gstin": False,
            "invoice_no": False,
            "date": False,
            "total_amount": False,
            "tax_keywords": False
        }

        # 1. GSTIN Regex Check (Highest priority!)
        gstin_match = re.search(config.GSTIN_REGEX, text)
        if gstin_match:
            matches["gstin"] = True

        # 2. Invoice Number keywords
        if re.search(r"(?i)\b(invoice|inv|bill)\s*(?:no|num|number|#)?[:\s\.-]*[A-Z0-9/-]+", text):
            matches["invoice_no"] = True

        # 3. Date pattern
        if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", text, re.IGNORECASE):
            matches["date"] = True

        # 4. Total Amount pattern
        if re.search(r"(?i)\b(total|grand\s+total|amount\s+payable|net\s+amount)\b", text):
            matches["total_amount"] = True

        # 5. Tax Keywords
        if re.search(r"(?i)\b(cgst|sgst|igst|gst|tax|hsn|sac)\b", text):
            matches["tax_keywords"] = True

        # Scoring weights for field presence
        score = 0.0
        if matches["gstin"]:
            score += 35.0  # Huge boost for valid GSTIN hit
        if matches["invoice_no"]:
            score += 20.0
        if matches["total_amount"]:
            score += 20.0
        if matches["date"]:
            score += 15.0
        if matches["tax_keywords"]:
            score += 10.0

        return min(100.0, score), matches

    @staticmethod
    def _evaluate_word_quality(text: str) -> Tuple[float, float]:
        """Calculates proportion of valid clean text vs garbage characters."""
        words = text.split()
        if not words:
            return 0.0, 1.0

        garbage_count = 0
        valid_count = 0

        for w in words:
            # Check for high density of weird non-ascii or non-printable symbols
            clean_w = re.sub(r'[^a-zA-Z0-9]', '', w)
            if len(clean_w) == 0:
                garbage_count += 1
            elif len(clean_w) >= 2:
                valid_count += 1

        total = len(words)
        noise_ratio = garbage_count / total if total > 0 else 0.0
        valid_ratio = valid_count / total if total > 0 else 0.0

        word_score = valid_ratio * 100.0
        return min(100.0, word_score), noise_ratio
