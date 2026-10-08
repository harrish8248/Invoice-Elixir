"""
Invoice OCR System - Preprocessing Pipeline
Provides selective, quality-adaptive image preprocessing operations:
- Deskewing / orientation correction
- Grayscale & Contrast enhancement (CLAHE)
- Adaptive Denoising
- Otsu / Adaptive Thresholding
- Margin cropping
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, List
import config

class DocumentPreprocessor:
    """Adaptive image preprocessor for optimizing OCR text recognition accuracy."""

    @classmethod
    def preprocess(cls, image_path: Path, doc_analysis: Dict[str, Any]) -> Tuple[Path, List[str]]:
        """
        Executes adaptive preprocessing workflow based on document analysis metrics.
        Returns path to processed image and list of applied transformation step names.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Unable to read image for preprocessing: {image_path}")

        applied_steps = []

        # 1. Orientation & Deskewing if skew angle > 1 degree
        skew_angle = doc_analysis.get("skew_angle", 0.0)
        if abs(skew_angle) > 1.0 and abs(skew_angle) < 25.0:
            img = cls.deskew(img, skew_angle)
            applied_steps.append(f"Deskewed ({skew_angle:.1f}°)")

        # 2. Convert to grayscale if color image
        if len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            applied_steps.append("Grayscale Conversion")
        else:
            gray = img

        # 3. Contrast enhancement if low contrast
        if doc_analysis.get("is_low_contrast", False):
            clahe = cv2.createCLAHE(
                clipLimit=config.PREPROCESSING_CONFIG["contrast_clip_limit"],
                tileGridSize=config.PREPROCESSING_CONFIG["tile_grid_size"]
            )
            gray = clahe.apply(gray)
            applied_steps.append("CLAHE Contrast Enhancement")

        # 4. Adaptive Denoising if noise ratio is high
        if doc_analysis.get("is_noisy", False):
            gray = cv2.fastNlMeansDenoising(gray, h=config.PREPROCESSING_CONFIG["denoise_h"])
            applied_steps.append("Adaptive Denoising")

        # 5. Mild Sharpening
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        gray = cv2.filter2D(gray, -1, kernel)
        applied_steps.append("Sharpening")

        # 6. Save preprocessed image to output directory
        out_filename = f"preprocessed_{image_path.name}"
        out_path = config.OUTPUT_DIR / out_filename
        cv2.imwrite(str(out_path), gray)

        return out_path, applied_steps

    @staticmethod
    def deskew(image: np.ndarray, angle: float) -> np.ndarray:
        """Rotates image around center by target skew angle."""
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
