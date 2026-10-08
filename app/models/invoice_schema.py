"""
Invoice OCR Processing System - Pydantic Data Models
Defines structured schema for field results, line items, invoice data,
OCR processing logs, and API response structures.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FieldResult(BaseModel):
    """
    Encapsulates an extracted value along with its confidence score,
    validation status, and potential warning messages.
    Never silently invents or mutates missing values.
    """
    value: Optional[str] = "Not detected"
    raw_value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = Field(default="Not Detected", description="Valid | Warning | Review Required | Not Detected")
    validation_message: Optional[str] = None


class LineItem(BaseModel):
    """Structured line item entry inside an invoice."""
    description: FieldResult = Field(default_factory=FieldResult)
    hsn_sac: FieldResult = Field(default_factory=FieldResult)
    quantity: FieldResult = Field(default_factory=FieldResult)
    unit_price: FieldResult = Field(default_factory=FieldResult)
    discount: FieldResult = Field(default_factory=FieldResult)
    tax_rate: FieldResult = Field(default_factory=FieldResult)
    taxable_value: FieldResult = Field(default_factory=FieldResult)
    cgst: FieldResult = Field(default_factory=FieldResult)
    sgst: FieldResult = Field(default_factory=FieldResult)
    igst: FieldResult = Field(default_factory=FieldResult)
    total: FieldResult = Field(default_factory=FieldResult)


class InvoiceData(BaseModel):
    """Comprehensive structured invoice data payload."""
    # Priority Fields - GSTIN First
    supplier_gstin: FieldResult = Field(default_factory=FieldResult)
    supplier_name: FieldResult = Field(default_factory=FieldResult)
    supplier_address: FieldResult = Field(default_factory=FieldResult)

    buyer_gstin: FieldResult = Field(default_factory=FieldResult)
    buyer_name: FieldResult = Field(default_factory=FieldResult)
    buyer_address: FieldResult = Field(default_factory=FieldResult)

    invoice_number: FieldResult = Field(default_factory=FieldResult)
    invoice_date: FieldResult = Field(default_factory=FieldResult)
    due_date: FieldResult = Field(default_factory=FieldResult)
    po_number: FieldResult = Field(default_factory=FieldResult)
    payment_terms: FieldResult = Field(default_factory=FieldResult)
    contact_email: FieldResult = Field(default_factory=FieldResult)
    contact_phone: FieldResult = Field(default_factory=FieldResult)
    bank_details: FieldResult = Field(default_factory=FieldResult)
    currency: FieldResult = Field(default_factory=FieldResult)

    # Financial & Tax Totals
    taxable_amount: FieldResult = Field(default_factory=FieldResult)
    cgst: FieldResult = Field(default_factory=FieldResult)
    sgst: FieldResult = Field(default_factory=FieldResult)
    igst: FieldResult = Field(default_factory=FieldResult)
    subtotal: FieldResult = Field(default_factory=FieldResult)
    round_off: FieldResult = Field(default_factory=FieldResult)
    total_amount: FieldResult = Field(default_factory=FieldResult)

    # Line items table
    line_items: List[LineItem] = Field(default_factory=list)


class OCREngineAttempt(BaseModel):
    """Log entry for an attempted OCR engine execution."""
    engine_name: str
    confidence: float
    quality_score: float
    accepted: bool
    rejection_reason: Optional[str] = None
    execution_time_ms: float = 0.0


class OCRProcessingDetails(BaseModel):
    """Detailed metadata and audit log of the OCR routing, evaluation, and fallback."""
    selected_engine: str
    final_confidence: float
    final_quality_score: float
    attempts: List[OCREngineAttempt] = Field(default_factory=list)
    preprocessing_applied: List[str] = Field(default_factory=list)
    document_type: str = "Unknown"  # Digital PDF, Scanned PDF, Image, Mixed PDF
    page_count: int = 1
    raw_text: str = ""
    preview_image_url: Optional[str] = None
    page_width: Optional[int] = None
    page_height: Optional[int] = None
    words: List[Dict[str, Any]] = Field(default_factory=list)



class ValidationResult(BaseModel):
    """Overall validation layer result including GSTIN and financial consistency checks."""
    overall_status: str = Field(default="PASS", description="PASS | WARNING | FAIL")
    gstin_validation: Dict[str, Any] = Field(default_factory=dict)
    math_consistency: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class InvoiceProcessingResponse(BaseModel):
    """API response model containing full processing output."""
    success: bool = True
    filename: str
    safe_internal_filename: str
    file_size_bytes: int
    processing_log: List[str] = Field(default_factory=list)
    ocr_details: OCRProcessingDetails
    invoice_data: InvoiceData
    validation: ValidationResult
