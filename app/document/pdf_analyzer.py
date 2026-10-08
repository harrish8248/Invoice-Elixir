"""
Invoice OCR System - PDF Inspection Module
Uses PyMuPDF (fitz) to inspect PDF files:
- Detects selectable text vs scanned image pages vs mixed content
- Extracts digital text directly when available
- Renders image pages to high-resolution pixmaps for OCR processing
- Analyzes text quality and presence of invoice keyword patterns
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import config

class PDFAnalyzer:
    """Inspects and processes PDF invoices using PyMuPDF."""

    @classmethod
    def inspect_pdf(cls, file_path: Path) -> Dict[str, Any]:
        """
        Analyzes PDF page by page to determine content type:
        - 'digital': text extractable directly from PDF vector stream
        - 'scanned': image-only PDF pages needing full OCR
        - 'mixed': combination of vector text and embedded scanned images
        """
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Failed to open or parse PDF document: {str(e)}")

        page_count = len(doc)
        page_analyses = []
        total_text_length = 0
        total_images_count = 0
        extracted_text_pages = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()
            images = page.get_images(full=True)
            
            text_len = len(text)
            total_text_length += text_len
            total_images_count += len(images)
            extracted_text_pages.append(text)

            is_scanned = text_len < 30  # Very low text count indicates scanned image
            page_analyses.append({
                "page_num": page_num + 1,
                "text_length": text_len,
                "image_count": len(images),
                "is_scanned": is_scanned,
                "extracted_text": text
            })

        doc.close()

        # Classify document overall type
        scanned_pages = sum(1 for p in page_analyses if p["is_scanned"])
        if scanned_pages == page_count:
            doc_type = "Scanned PDF"
        elif scanned_pages == 0:
            doc_type = "Digital PDF"
        else:
            doc_type = "Mixed PDF"

        full_extracted_text = "\n\n--- PAGE BREAK ---\n\n".join(extracted_text_pages)

        return {
            "document_type": doc_type,
            "page_count": page_count,
            "page_analyses": page_analyses,
            "total_text_length": total_text_length,
            "total_images_count": total_images_count,
            "digital_text": full_extracted_text
        }

    @classmethod
    def render_pdf_to_images(cls, file_path: Path, dpi: int = 300) -> List[Path]:
        """
        Renders PDF pages to high-resolution image files for OCR processing.
        Saves rendered images in output/temp directory.
        """
        doc = fitz.open(file_path)
        rendered_paths = []
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image_filename = f"{file_path.stem}_p{page_num + 1}.png"
            image_path = config.OUTPUT_DIR / image_filename
            pix.save(str(image_path))
            rendered_paths.append(image_path)

        doc.close()
        return rendered_paths
