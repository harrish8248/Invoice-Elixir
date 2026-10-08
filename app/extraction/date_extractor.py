"""
Invoice OCR System - Date Extractor Module
Extracts and normalizes invoice issue date and payment due date.
"""

import re
from typing import Tuple, Optional
from app.models.invoice_schema import FieldResult
from app.extraction.regex_patterns import DATE_PATTERNS

class DateExtractor:
    """Extracts date strings and classifies Invoice Date vs Due Date."""

    @classmethod
    def extract_dates(cls, text: str) -> Tuple[FieldResult, FieldResult]:
        """Returns (invoice_date_result, due_date_result)."""
        lines = text.splitlines()
        inv_date_cand = None
        due_date_cand = None

        for line in lines:
            line_lower = line.lower()
            for pattern in DATE_PATTERNS:
                matches = pattern.findall(line)
                for match in matches:
                    date_str = match.strip() if isinstance(match, str) else match[0].strip()
                    if "due" in line_lower:
                        if not due_date_cand:
                            due_date_cand = (date_str, line)
                    elif any(k in line_lower for k in ["date", "invoice date", "dated", "dt"]):
                        if not inv_date_cand:
                            inv_date_cand = (date_str, line)

        # Fallback if unlabelled date found
        if not inv_date_cand:
            for pattern in DATE_PATTERNS:
                m = pattern.search(text)
                if m:
                    d = m.group(1) if m.groups() else m.group(0)
                    inv_date_cand = (d.strip(), m.group(0))
                    break

        inv_res = cls._build_date_result(inv_date_cand, "Invoice Date")
        due_res = cls._build_date_result(due_date_cand, "Due Date")

        return inv_res, due_res

    @staticmethod
    def _build_date_result(cand: Optional[Tuple[str, str]], label: str) -> FieldResult:
        if not cand:
            return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
        date_val, line_raw = cand
        return FieldResult(
            value=date_val,
            raw_value=line_raw,
            confidence=88.0,
            status="Valid"
        )
