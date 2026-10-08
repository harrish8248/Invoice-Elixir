"""
Invoice OCR System - End-to-End Invoice Processing Service
Orchestrates the complete pipeline according to system specifications:
FILE INTAKE -> SECURITY VALIDATION -> DOCUMENT INSPECTION -> PREPROCESSING ->
OCR ROUTER -> OCR EXECUTION -> OCR QUALITY EVALUATION -> RETRY FALLBACK ->
BEST RESULT SELECTION -> INVOICE EXTRACTION -> FIELD VALIDATION -> RESPONSE ASSEMBLY
"""

import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
import config
from app.security.file_validator import FileValidator
from app.document.pdf_analyzer import PDFAnalyzer
from app.document.document_analyzer import DocumentAnalyzer
from app.document.preprocessor import DocumentPreprocessor
from app.ocr.router import OCRRouter
from app.ocr.evaluator import OCREvaluator
from app.ocr.base import OCRResult
from app.extraction.invoice_extractor import InvoiceExtractor
from app.validation.invoice_validator import InvoiceValidator
from app.models.invoice_schema import (
    InvoiceProcessingResponse, OCRProcessingDetails, OCREngineAttempt, InvoiceData
)

class InvoiceProcessingService:
    """Master service executing end-to-end invoice processing."""

    def __init__(self):
        self.router = OCRRouter()

    def process_invoice(self, original_filename: str, content_bytes: bytes) -> InvoiceProcessingResponse:
        """Executes full pipeline for an uploaded invoice file."""
        log: List[str] = []
        log.append("File received.")

        # 1. Security & File Validation
        safe_name, file_path, size_bytes, mime_type = FileValidator.validate_and_save(
            original_filename, content_bytes
        )
        log.append("Security validation: PASS")
        log.append(f"File size: {size_bytes / (1024*1024):.2f} MB")
        log.append(f"File type: {mime_type}")

        # 2. Document Inspection
        is_pdf = safe_name.lower().endswith(".pdf")
        images_to_process: List[Path] = []
        doc_inspection: Dict[str, Any] = {}

        if is_pdf:
            doc_inspection = PDFAnalyzer.inspect_pdf(file_path)
            doc_type = doc_inspection["document_type"]
            log.append(f"PDF inspection: {doc_type} ({doc_inspection['page_count']} page(s))")

            # Render PDF pages to high-res images for OCR pipeline
            rendered_images = PDFAnalyzer.render_pdf_to_images(file_path)
            images_to_process.extend(rendered_images)
        else:
            doc_type = "Image Document"
            doc_inspection = {"document_type": doc_type, "page_count": 1}
            images_to_process.append(file_path)

        # Process first page image for engine routing & OCR evaluation
        primary_image = images_to_process[0]
        
        # Save a preview copy in output directory for frontend display
        preview_filename = f"{safe_name}_preview.png"
        preview_path = config.OUTPUT_DIR / preview_filename
        try:
            from PIL import Image as PILImage
            img = PILImage.open(primary_image)
            img.save(preview_path, format="PNG")
            preview_url = f"/outputs/{preview_filename}"
        except Exception:
            preview_url = None

        doc_analysis = DocumentAnalyzer.analyze_image(primary_image)

        # 3. Document Preprocessing
        preprocessed_image, applied_steps = DocumentPreprocessor.preprocess(primary_image, doc_analysis)
        log.append(f"Preprocessing: applied ({', '.join(applied_steps)})")


        # 4. OCR Routing
        ranked_engines = self.router.get_ranked_engines(doc_inspection, doc_analysis)
        if not ranked_engines:
            raise RuntimeError("No enabled OCR engines available in configuration.")

        top_engine_name = ranked_engines[0][0].name
        log.append(f"OCR Router: {top_engine_name} selected as primary engine")

        # 5. OCR Execution & Retry Fallback Loop
        attempts: List[OCREngineAttempt] = []
        ocr_results: List[Tuple[OCRResult, float]] = []  # (ocr_res, quality_score)
        
        selected_final_ocr: OCRResult = None
        selected_final_score: float = 0.0
        selected_engine_name: str = ""

        retry_count = 0
        for engine, router_score, rationale in ranked_engines:
            if retry_count >= config.MAX_OCR_RETRIES:
                log.append(f"Maximum retry limit ({config.MAX_OCR_RETRIES}) reached.")
                break

            if not engine.available:
                attempts.append(OCREngineAttempt(
                    engine_name=engine.name,
                    confidence=0.0,
                    quality_score=0.0,
                    accepted=False,
                    rejection_reason=f"Engine unavailable: {engine.init_error}"
                ))
                continue

            # Run OCR
            ocr_res = engine.process_image(preprocessed_image)
            quality_score, breakdown, passes = OCREvaluator.evaluate(ocr_res)
            
            log.append(f"Executed engine: {engine.name} | OCR confidence: {ocr_res.confidence}%")
            log.append(f"Quality score for {engine.name}: {quality_score}%")

            attempt_entry = OCREngineAttempt(
                engine_name=engine.name,
                confidence=ocr_res.confidence,
                quality_score=quality_score,
                accepted=passes,
                rejection_reason=None if passes else f"Quality score {quality_score}% below threshold {config.OCR_ACCEPT_THRESHOLD}%",
                execution_time_ms=ocr_res.execution_time_ms
            )
            attempts.append(attempt_entry)
            ocr_results.append((ocr_res, quality_score))

            if passes:
                log.append(f"Quality threshold MET ({quality_score}% >= {config.OCR_ACCEPT_THRESHOLD}%). Accepting {engine.name} result.")
                selected_final_ocr = ocr_res
                selected_final_score = quality_score
                selected_engine_name = engine.name
                break
            else:
                log.append(f"Quality threshold NOT MET ({quality_score}% < {config.OCR_ACCEPT_THRESHOLD}%). Triggering fallback retry.")
                retry_count += 1

        # Fallback: if no engine passed threshold, select the best scoring result among all attempted
        if not selected_final_ocr and ocr_results:
            best_tuple = max(ocr_results, key=lambda x: x[1])
            selected_final_ocr = best_tuple[0]
            selected_final_score = best_tuple[1]
            selected_engine_name = selected_final_ocr.engine_name
            log.append(f"No engine met threshold. Selected best result: {selected_engine_name} ({selected_final_score}%)")
        elif not selected_final_ocr:
            # Fallback if digital PDF text is available
            digital_txt = doc_inspection.get("digital_text", "")
            selected_final_ocr = OCRResult(
                engine_name="PyMuPDF Vector Text",
                full_text=digital_txt,
                confidence=95.0
            )
            selected_final_score = 80.0
            selected_engine_name = "PyMuPDF Vector Text"

        log.append(f"Selected final engine: {selected_engine_name}")

        # 6. Structured Invoice Field Extraction (GSTIN First)
        raw_text = selected_final_ocr.full_text
        invoice_data = InvoiceExtractor.extract_invoice_data(raw_text)
        log.append("Invoice field extraction completed.")

        # 7. Field & Financial Consistency Validation
        validation = InvoiceValidator.validate_invoice(invoice_data)
        log.append(f"GSTIN validation: {'PASS' if invoice_data.supplier_gstin.status == 'Valid' else 'REVIEW REQUIRED'}")
        log.append(f"Invoice validation: {validation.overall_status}")
        log.append("Processing completed.")

        # Extract image dimensions for spatial coordinates
        page_width = None
        page_height = None
        try:
            from PIL import Image as PILImage
            with PILImage.open(primary_image) as p_img:
                page_width, page_height = p_img.width, p_img.height
        except Exception:
            pass

        # Serialize word bounding boxes
        words_data = []
        if selected_final_ocr and selected_final_ocr.words:
            for w in selected_final_ocr.words:
                words_data.append({
                    "text": w.text,
                    "confidence": round(w.confidence, 1),
                    "bbox": [round(coord, 1) for coord in w.bbox] if w.bbox else None
                })

        ocr_details = OCRProcessingDetails(
            selected_engine=selected_engine_name,
            final_confidence=selected_final_ocr.confidence,
            final_quality_score=selected_final_score,
            attempts=attempts,
            preprocessing_applied=applied_steps,
            document_type=doc_type,
            page_count=doc_inspection.get("page_count", 1),
            raw_text=raw_text,
            preview_image_url=preview_url,
            page_width=page_width,
            page_height=page_height,
            words=words_data
        )


        return InvoiceProcessingResponse(
            success=True,
            filename=original_filename,
            safe_internal_filename=safe_name,
            file_size_bytes=size_bytes,
            processing_log=log,
            ocr_details=ocr_details,
            invoice_data=invoice_data,
            validation=validation
        )
