"""
Invoice OCR System - GSTIN Priority Extraction Module
Extracts, ranks, and categorizes Supplier vs Buyer GSTINs from OCR text.
Ensures GSTIN is treated with HIGHEST extraction priority.
Never invents or fabricates GSTIN values.
"""

import re
from typing import Tuple, List, Dict, Optional
from app.models.invoice_schema import FieldResult
from app.extraction.regex_patterns import GSTIN_PATTERN

# Valid Indian State Codes (01 to 38, 97, 99)
VALID_STATE_CODES = {
    f"{i:02d}" for i in range(1, 39)
}.union({"97", "99"})

class GSTINExtractor:
    """Specialized priority extractor for Indian Goods and Services Tax Identification Numbers (GSTIN)."""

    @classmethod
    def extract_gstins(cls, text: str) -> Tuple[FieldResult, FieldResult]:
        """
        Extracts Supplier GSTIN and Buyer GSTIN from full text.
        Returns: (supplier_gstin_result, buyer_gstin_result)
        """
        lines = text.splitlines()
        raw_candidates = []

        for line_idx, line in enumerate(lines):
            matches = GSTIN_PATTERN.findall(line)
            for candidate in matches:
                clean_cand = candidate.strip().upper()
                raw_candidates.append({
                    "gstin": clean_cand,
                    "line_idx": line_idx,
                    "line_text": line,
                    "valid_structure": cls.validate_gstin_structure(clean_cand)
                })

        if not raw_candidates:
            empty_supplier = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
            empty_buyer = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
            return empty_supplier, empty_buyer

        # Contextual mapping: Supplier GSTIN vs Buyer GSTIN
        supplier_cand = None
        buyer_cand = None

        for cand in raw_candidates:
            gst = cand["gstin"]
            line = cand["line_text"].lower()

            # Check explicit labels
            if any(k in line for k in ["buyer", "customer", "bill to", "consignee"]):
                if not buyer_cand:
                    buyer_cand = cand
            elif any(k in line for k in ["supplier", "seller", "vendor", "billed by"]):
                if not supplier_cand:
                    supplier_cand = cand
            else:
                # Top half of document (line_idx < half) favors supplier
                if cand["line_idx"] < (len(lines) / 2):
                    if not supplier_cand:
                        supplier_cand = cand
                else:
                    if not buyer_cand and cand != supplier_cand:
                        buyer_cand = cand

        # Fallback if both assigned same or one missing
        if not supplier_cand and raw_candidates:
            supplier_cand = raw_candidates[0]

        if not buyer_cand and len(raw_candidates) > 1:
            buyer_cand = [c for c in raw_candidates if c != supplier_cand][0]

        supplier_res = cls._build_field_result(supplier_cand)
        buyer_res = cls._build_field_result(buyer_cand)

        return supplier_res, buyer_res

    @classmethod
    def validate_gstin_structure(cls, gstin: str) -> bool:
        """Checks 15-character structure and valid state code prefix."""
        if len(gstin) != 15:
            return False
        state_code = gstin[:2]
        if state_code not in VALID_STATE_CODES:
            return False
        # 14th character must be 'Z'
        if gstin[13] != 'Z':
            return False
        return True

    @classmethod
    def _build_field_result(cls, candidate_dict: Optional[Dict]) -> FieldResult:
        if not candidate_dict:
            return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")

        gst = candidate_dict["gstin"]
        is_valid = candidate_dict["valid_structure"]

        if is_valid:
            return FieldResult(
                value=gst,
                raw_value=candidate_dict["line_text"],
                confidence=96.0,
                status="Valid",
                validation_message="GSTIN pattern and state code verified."
            )
        else:
            return FieldResult(
                value=gst,
                raw_value=candidate_dict["line_text"],
                confidence=70.0,
                status="Review Required",
                validation_message="GSTIN detected but state code or checksum structure requires verification."
            )
