"""
Invoice OCR System - Financial & Amount Extractor Module
Extracts financial totals, tax components (CGST, SGST, IGST), taxable amounts, subtotal, round-off, and grand total.
"""

import re
from typing import Dict, Any, Optional, Tuple
from app.models.invoice_schema import FieldResult
from app.extraction.regex_patterns import AMOUNT_PATTERN

class AmountExtractor:
    """Extracts numeric financial amounts and tax breakdowns from OCR text."""

    @classmethod
    def extract_amounts(cls, text: str) -> Dict[str, FieldResult]:
        """
        Parses financial fields:
        - taxable_amount
        - cgst
        - sgst
        - igst
        - subtotal
        - round_off
        - total_amount
        """
        lines = text.splitlines()

        extracted = {
            "taxable_amount": FieldResult(),
            "cgst": FieldResult(),
            "sgst": FieldResult(),
            "igst": FieldResult(),
            "subtotal": FieldResult(),
            "round_off": FieldResult(),
            "total_amount": FieldResult()
        }

        for line in lines:
            line_lower = line.lower()
            amounts = cls._extract_numbers_from_line(line)

            if not amounts:
                continue

            val_str = f"{max(amounts):.2f}"
            val_raw = line

            if any(k in line_lower for k in ["grand total", "total amount", "net payable", "invoice total", "amount payable"]) and not extracted["total_amount"].value != "Not detected":
                extracted["total_amount"] = FieldResult(value=val_str, raw_value=val_raw, confidence=92.0, status="Valid")
            elif "taxable" in line_lower and extracted["taxable_amount"].value == "Not detected":
                extracted["taxable_amount"] = FieldResult(value=val_str, raw_value=val_raw, confidence=90.0, status="Valid")
            elif "cgst" in line_lower and extracted["cgst"].value == "Not detected":
                extracted["cgst"] = FieldResult(value=val_str, raw_value=val_raw, confidence=88.0, status="Valid")
            elif "sgst" in line_lower and extracted["sgst"].value == "Not detected":
                extracted["sgst"] = FieldResult(value=val_str, raw_value=val_raw, confidence=88.0, status="Valid")
            elif "igst" in line_lower and extracted["igst"].value == "Not detected":
                extracted["igst"] = FieldResult(value=val_str, raw_value=val_raw, confidence=88.0, status="Valid")
            elif "subtotal" in line_lower and extracted["subtotal"].value == "Not detected":
                extracted["subtotal"] = FieldResult(value=val_str, raw_value=val_raw, confidence=85.0, status="Valid")
            elif "round off" in line_lower and extracted["round_off"].value == "Not detected":
                extracted["round_off"] = FieldResult(value=val_str, raw_value=val_raw, confidence=85.0, status="Valid")

        # Fallback for total_amount if keyword didn't trigger: find max monetary figure near end of document
        if extracted["total_amount"].value == "Not detected":
            all_numbers = []
            for l in lines[-15:]:  # bottom 15 lines
                nums = cls._extract_numbers_from_line(l)
                if nums:
                    all_numbers.extend(nums)
            if all_numbers:
                max_val = max(all_numbers)
                extracted["total_amount"] = FieldResult(
                    value=f"{max_val:.2f}",
                    confidence=75.0,
                    status="Review Required",
                    validation_message="Inferred from largest monetary figure at bottom of invoice."
                )

        return extracted

    @staticmethod
    def _extract_numbers_from_line(line: str) -> list[float]:
        """Parses floating-point monetary numbers from a line string."""
        found = []
        matches = AMOUNT_PATTERN.findall(line)
        for m in matches:
            clean_str = m.replace(",", "").strip()
            try:
                val = float(clean_str)
                # Ignore plain zip codes or small integers unless decimal points present
                if val > 0.0 and ("." in clean_str or val > 100):
                    found.append(val)
            except ValueError:
                continue
        return found
