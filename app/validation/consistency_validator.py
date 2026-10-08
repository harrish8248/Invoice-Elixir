"""
Invoice OCR System - Mathematical Consistency Validator
Verifies tax calculations:
Taxable Amount + CGST + SGST + IGST + Round Off approx equals Grand Total.
Does NOT silently mutate extracted numbers; reports warning if discrepancy detected.
"""

from typing import Dict, Any
import config
from app.models.invoice_schema import InvoiceData

class ConsistencyValidator:
    """Validates mathematical relationship between taxable values, tax breakdown, and grand total."""

    @classmethod
    def validate_totals(cls, invoice_data: InvoiceData) -> Dict[str, Any]:
        """
        Calculates expected grand total and compares with extracted total.
        Returns validation dictionary with status, expected vs actual values, and difference.
        """
        def parse_val(field_res) -> float:
            if not field_res or field_res.value == "Not detected":
                return 0.0
            try:
                return float(str(field_res.value).replace(",", ""))
            except ValueError:
                return 0.0

        taxable = parse_val(invoice_data.taxable_amount)
        cgst = parse_val(invoice_data.cgst)
        sgst = parse_val(invoice_data.sgst)
        igst = parse_val(invoice_data.igst)
        round_off = parse_val(invoice_data.round_off)
        grand_total = parse_val(invoice_data.total_amount)

        if grand_total == 0.0:
            return {
                "status": "Warning",
                "message": "Grand total not extracted; skipping mathematical balance verification.",
                "calculated_total": round(taxable + cgst + sgst + igst + round_off, 2),
                "extracted_total": 0.0,
                "difference": 0.0
            }

        calculated_total = taxable + cgst + sgst + igst + round_off
        diff = abs(calculated_total - grand_total)
        max_allowed_diff = grand_total * (config.AMOUNT_TOLERANCE_PERCENT / 100.0)

        # Allow minimum absolute 2.0 currency unit tolerance for small rounding errors
        is_consistent = diff <= max(2.0, max_allowed_diff) or taxable == 0.0

        return {
            "status": "PASS" if is_consistent else "WARNING",
            "message": "Tax calculations mathematically consistent." if is_consistent else f"Discrepancy detected: Taxable ({taxable}) + CGST ({cgst}) + SGST ({sgst}) + IGST ({igst}) = {calculated_total:.2f}, but extracted Grand Total is {grand_total:.2f}.",
            "taxable_amount": taxable,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "round_off": round_off,
            "calculated_total": round(calculated_total, 2),
            "extracted_total": round(grand_total, 2),
            "difference": round(diff, 2)
        }
