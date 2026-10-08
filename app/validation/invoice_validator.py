"""
Invoice OCR System - Master Invoice Validation Layer
Combines GSTIN validation and financial consistency checks into a unified ValidationResult payload.
"""

from typing import List
from app.models.invoice_schema import InvoiceData, ValidationResult
from app.validation.gstin_validator import GSTINValidator
from app.validation.consistency_validator import ConsistencyValidator

class InvoiceValidator:
    """Master validator runner."""

    @classmethod
    def validate_invoice(cls, invoice_data: InvoiceData) -> ValidationResult:
        """Executes full suite of invoice validation checks."""
        warnings: List[str] = []

        # 1. Supplier GSTIN Validation
        supplier_gst_val = GSTINValidator.validate_gstin(invoice_data.supplier_gstin.value)
        if not supplier_gst_val["valid"] and invoice_data.supplier_gstin.value != "Not detected":
            warnings.append(f"Supplier GSTIN warning: {supplier_gst_val['message']}")

        # 2. Buyer GSTIN Validation
        buyer_gst_val = GSTINValidator.validate_gstin(invoice_data.buyer_gstin.value)
        if not buyer_gst_val["valid"] and invoice_data.buyer_gstin.value != "Not detected":
            warnings.append(f"Buyer GSTIN warning: {buyer_gst_val['message']}")

        # 3. Tax Consistency Check
        math_check = ConsistencyValidator.validate_totals(invoice_data)
        if math_check["status"] == "WARNING":
            warnings.append(math_check["message"])

        # 4. Mandatory Field Warnings
        if invoice_data.supplier_gstin.value == "Not detected":
            warnings.append("Supplier GSTIN is not detected on the invoice.")
        if invoice_data.invoice_number.value == "Not detected":
            warnings.append("Invoice Number is not detected.")
        if invoice_data.total_amount.value == "Not detected":
            warnings.append("Total Invoice Amount is not detected.")

        overall_status = "PASS" if not warnings else "WARNING"

        return ValidationResult(
            overall_status=overall_status,
            gstin_validation={
                "supplier_gstin": supplier_gst_val,
                "buyer_gstin": buyer_gst_val
            },
            math_consistency=math_check,
            warnings=warnings
        )
