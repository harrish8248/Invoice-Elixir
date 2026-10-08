"""
Invoice OCR System - Financial Consistency & Invoice Validation Tests
"""

from app.models.invoice_schema import InvoiceData, FieldResult
from app.validation.consistency_validator import ConsistencyValidator
from app.validation.invoice_validator import InvoiceValidator

def test_financial_consistency_pass():
    inv_data = InvoiceData(
        taxable_amount=FieldResult(value="1000.00"),
        cgst=FieldResult(value="90.00"),
        sgst=FieldResult(value="90.00"),
        igst=FieldResult(value="0.00"),
        total_amount=FieldResult(value="1180.00")
    )

    result = ConsistencyValidator.validate_totals(inv_data)
    assert result["status"] == "PASS"
    assert result["calculated_total"] == 1180.00
    assert result["extracted_total"] == 1180.00

def test_financial_consistency_warning_on_discrepancy():
    inv_data = InvoiceData(
        taxable_amount=FieldResult(value="1000.00"),
        cgst=FieldResult(value="90.00"),
        sgst=FieldResult(value="90.00"),
        total_amount=FieldResult(value="1500.00")  # Discrepancy!
    )

    result = ConsistencyValidator.validate_totals(inv_data)
    assert result["status"] == "WARNING"
    assert "Discrepancy detected" in result["message"]

def test_invoice_master_validator():
    inv_data = InvoiceData(
        supplier_gstin=FieldResult(value="29ABCDE1234F1ZW", status="Valid"),
        invoice_number=FieldResult(value="INV-101", status="Valid"),
        taxable_amount=FieldResult(value="500.00"),
        total_amount=FieldResult(value="500.00")
    )

    val = InvoiceValidator.validate_invoice(inv_data)
    assert val.overall_status == "PASS"


