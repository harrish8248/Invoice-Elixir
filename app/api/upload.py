"""
Invoice OCR System - Upload & Processing API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.processing_service import InvoiceProcessingService
from app.security.file_validator import SecurityValidationError
from app.models.invoice_schema import InvoiceProcessingResponse

router = APIRouter(prefix="/api", tags=["Invoice Processing"])
service = InvoiceProcessingService()

@router.post("/upload", response_model=InvoiceProcessingResponse)
async def process_invoice_upload(file: UploadFile = File(...)):
    """
    Intake endpoint for invoice files (.pdf, .png, .jpg, .jpeg).
    Executes security checks, OCR routing, quality evaluation, retry logic,
    GSTIN-priority field extraction, and tax consistency validation.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename missing from upload request."
        )

    try:
        content_bytes = await file.read()
        response = service.process_invoice(file.filename, content_bytes)
        return response
    except SecurityValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Validation Failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice processing error: {str(e)}"
        )
