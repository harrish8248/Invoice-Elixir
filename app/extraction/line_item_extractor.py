"""
Invoice OCR System - Line Item Table Extractor Module
Parses tabular line items (description, HSN/SAC, quantity, unit price, tax rate, taxable value, total).
Only extracts line items if recognizable table structure or columns are present.
"""

import re
from typing import List
from app.models.invoice_schema import LineItem, FieldResult
from app.extraction.regex_patterns import HSN_SAC_PATTERN

class LineItemExtractor:
    """Extracts line items from tabular OCR text blocks."""

    @classmethod
    def extract_line_items(cls, text: str) -> List[LineItem]:
        """
        Scans for line items table header and table row patterns.
        Returns list of LineItem pydantic models.
        """
        lines = text.splitlines()
        items: List[LineItem] = []

        in_table_section = False
        header_index = -1

        table_keywords = ["description", "particulars", "item", "hsn", "qty", "quantity", "unit price", "rate", "amount"]

        for idx, line in enumerate(lines):
            line_lower = line.lower()
            matching_keywords = sum(1 for k in table_keywords if k in line_lower)

            if matching_keywords >= 2:
                in_table_section = True
                header_index = idx
                continue

            if in_table_section:
                # Stop if we hit total / summary keywords
                if any(k in line_lower for k in ["total", "subtotal", "taxable value", "amount in words", "bank details", "terms"]):
                    break

                # Parse tabular row candidate
                item = cls._parse_table_row(line)
                if item:
                    items.append(item)

        return items

    @staticmethod
    def _parse_table_row(line: str) -> LineItem | None:
        """Parses a single table row string into LineItem field components."""
        tokens = line.split()
        if len(tokens) < 3:
            return None

        # Check for HSN / SAC candidate
        hsn_match = HSN_SAC_PATTERN.search(line)
        hsn_val = hsn_match.group(1) if hsn_match else "Not detected"

        # Check numbers in row
        numbers = []
        desc_tokens = []

        for t in tokens:
            clean_t = t.replace(",", "")
            try:
                num = float(clean_t)
                numbers.append(num)
            except ValueError:
                desc_tokens.append(t)

        description_text = " ".join(desc_tokens).strip()
        if not description_text or len(description_text) < 3:
            return None

        qty_val = "Not detected"
        price_val = "Not detected"
        total_val = "Not detected"

        if len(numbers) >= 1:
            total_val = f"{numbers[-1]:.2f}"
        if len(numbers) >= 2:
            price_val = f"{numbers[-2]:.2f}"
        if len(numbers) >= 3:
            qty_val = f"{numbers[0]:.2f}"

        return LineItem(
            description=FieldResult(value=description_text, confidence=85.0, status="Valid"),
            hsn_sac=FieldResult(value=hsn_val, confidence=80.0 if hsn_val != "Not detected" else 0.0, status="Valid" if hsn_val != "Not detected" else "Not Detected"),
            quantity=FieldResult(value=qty_val, confidence=80.0 if qty_val != "Not detected" else 0.0, status="Valid" if qty_val != "Not detected" else "Not Detected"),
            unit_price=FieldResult(value=price_val, confidence=80.0 if price_val != "Not detected" else 0.0, status="Valid" if price_val != "Not detected" else "Not Detected"),
            total=FieldResult(value=total_val, confidence=85.0 if total_val != "Not detected" else 0.0, status="Valid" if total_val != "Not detected" else "Not Detected")
        )
