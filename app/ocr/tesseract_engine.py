"""
Invoice OCR Processing System - Tesseract OCR Engine Implementation
Wraps pytesseract with word-level bounding box and confidence extraction.
"""

import time
import os
import shutil
from pathlib import Path
from typing import Tuple, Optional
import pytesseract
from PIL import Image
import config
from app.ocr.base import BaseOCREngine, OCRResult, OCRWordBox

class TesseractOCREngine(BaseOCREngine):
    """Tesseract OCR Engine wrapper."""

    def __init__(self):
        # Configure executable path on Windows if specified
        if os.path.exists(config.TESSERACT_CMD):
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        super().__init__("Tesseract")

    def check_availability(self) -> Tuple[bool, Optional[str]]:
        """Verifies Tesseract binary availability."""
        cmd_path = pytesseract.pytesseract.tesseract_cmd
        if os.path.exists(cmd_path) or shutil.which("tesseract") is not None:
            try:
                ver = pytesseract.get_tesseract_version()
                return True, None
            except Exception as e:
                return False, f"Tesseract binary present but failed execution: {str(e)}"
        return False, f"Tesseract binary not found at '{cmd_path}' or system PATH."

    def process_image(self, image_path: Path) -> OCRResult:
        if not self.available:
            return OCRResult(
                engine_name=self.name,
                full_text="",
                confidence=0.0,
                is_available=False,
                error_message=self.init_error
            )

        start_time = time.time()
        try:
            img = Image.open(image_path)
            # Fetch detailed dataframe/dict containing word coordinates and confidence
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            words = []
            valid_confidences = []
            full_text_lines = []
            current_line = []
            last_line_num = -1

            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = float(data['conf'][i])
                line_num = data['line_num'][i]

                if line_num != last_line_num:
                    if current_line:
                        full_text_lines.append(" ".join(current_line))
                        current_line = []
                    last_line_num = line_num

                if text:
                    current_line.append(text)
                    if conf >= 0:  # -1 represents block/line headers
                        valid_confidences.append(conf)
                        words.append(OCRWordBox(
                            text=text,
                            confidence=conf,
                            bbox=[
                                float(data['left'][i]),
                                float(data['top'][i]),
                                float(data['left'][i] + data['width'][i]),
                                float(data['top'][i] + data['height'][i])
                            ]
                        ))

            if current_line:
                full_text_lines.append(" ".join(current_line))

            full_text = "\n".join(full_text_lines)
            avg_confidence = float(sum(valid_confidences) / len(valid_confidences)) if valid_confidences else 0.0
            exec_time = (time.time() - start_time) * 1000.0

            return OCRResult(
                engine_name=self.name,
                full_text=full_text,
                confidence=round(avg_confidence, 2),
                words=words,
                execution_time_ms=round(exec_time, 2)
            )

        except Exception as e:
            exec_time = (time.time() - start_time) * 1000.0
            return OCRResult(
                engine_name=self.name,
                full_text="",
                confidence=0.0,
                execution_time_ms=round(exec_time, 2),
                error_message=f"Tesseract OCR processing error: {str(e)}"
            )
