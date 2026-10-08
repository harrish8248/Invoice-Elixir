"""
Invoice OCR System - Security & File Validator Tests
"""

import pytest
import config
from app.security.file_validator import FileValidator, SecurityValidationError

def test_file_size_validation():
    # Valid size
    small_bytes = b"PDF-1.4 header text" * 10
    assert FileValidator.validate_file_size(small_bytes) == len(small_bytes)

    # Exceeding size (> 15MB)
    huge_bytes = b"0" * (15 * 1024 * 1024 + 100)
    with pytest.raises(SecurityValidationError) as exc:
        FileValidator.validate_file_size(huge_bytes)
    assert "exceeds maximum" in str(exc.value)

def test_extension_validation():
    assert FileValidator.validate_extension("invoice.pdf") == ".pdf"
    assert FileValidator.validate_extension("scan.PNG") == ".png"

    with pytest.raises(SecurityValidationError):
        FileValidator.validate_extension("malicious.exe")

def test_magic_bytes_validation():
    pdf_bytes = b"%PDF-1.5 fake content"
    assert FileValidator.validate_magic_bytes(pdf_bytes, ".pdf") == "application/pdf"

    png_bytes = b"\x89PNG\r\n\x1a\nfake content"
    assert FileValidator.validate_magic_bytes(png_bytes, ".png") == "image/png"

    with pytest.raises(SecurityValidationError):
        FileValidator.validate_magic_bytes(b"NOT_A_PDF", ".pdf")
