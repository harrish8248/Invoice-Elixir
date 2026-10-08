"""
Invoice OCR System - GSTIN Priority Extraction & Validation Tests
"""

from app.extraction.gstin_extractor import GSTINExtractor
from app.validation.gstin_validator import GSTINValidator

def test_gstin_checksum_validation():
    # Test valid Indian GSTIN pattern and checksum
    # 29ABCDE1234F1ZW
    val = GSTINValidator.validate_gstin("29ABCDE1234F1ZW")
    assert val["state_code"] == "29"
    assert val["pan"] == "ABCDE1234F"
    assert val["valid"] is True


    # Test invalid GSTIN length
    inv = GSTINValidator.validate_gstin("1234")
    assert inv["valid"] is False

    # Test missing GSTIN
    missing = GSTINValidator.validate_gstin("Not detected")
    assert missing["valid"] is False

def test_gstin_extraction_priority():
    sample_ocr_text = """
    TAX INVOICE
    ACME SUPPLIERS PRIVATE LIMITED
    GSTIN: 27AAAAA0000A1Z5
    Regd Office: Mumbai, Maharashtra

    Bill To:
    GLOBAL TECH SOLUTIONS
    GSTIN/UIN: 29BBBCC1111B1Z2
    Bangalore, Karnataka

    Invoice No: INV-2026-99
    Date: 12/09/2026
    """

    supplier_res, buyer_res = GSTINExtractor.extract_gstins(sample_ocr_text)

    assert supplier_res.value == "27AAAAA0000A1Z5"
    assert buyer_res.value == "29BBBCC1111B1Z2"
    assert supplier_res.status in ["Valid", "Review Required"]

def test_missing_gstin_never_invents_value():
    no_gst_text = "Plain Invoice without GST details. Total Amount: Rs 500"
    supplier_res, buyer_res = GSTINExtractor.extract_gstins(no_gst_text)

    assert supplier_res.value == "Not detected"
    assert buyer_res.value == "Not detected"
    assert supplier_res.confidence == 0.0
