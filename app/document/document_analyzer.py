"""
Invoice OCR System - Document Characteristics Analyzer
Analyzes input image / document features (skew, contrast, noise, layout complexity, resolution, tables)
to inform the OCR Router on optimal engine selection.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any

class DocumentAnalyzer:
    """Extracts optical & structural metrics from document images."""

    @classmethod
    def analyze_image(cls, image_path: Path) -> Dict[str, Any]:
        """
        Calculates metric indicators:
        - Image dimensions & resolution
        - Skew angle (Hough line transform / contour min area rect)
        - Contrast score (Standard deviation of pixel intensities)
        - Noise ratio (Difference between image and median filtered image)
        - Blur score (Laplacian variance)
        - Skew severity (None, Mild, High)
        - Estimated layout complexity
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not load image at path: {image_path}")

        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Blur evaluation via Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        is_blurry = blur_score < 100.0

        # 2. Contrast evaluation
        contrast_score = float(np.std(gray))
        is_low_contrast = contrast_score < 40.0

        # 3. Noise evaluation
        median = cv2.medianBlur(gray, 3)
        noise_diff = cv2.absdiff(gray, median)
        noise_ratio = float(np.mean(noise_diff))
        is_noisy = noise_ratio > 10.0

        # 4. Skew angle estimation using minAreaRect on binary text contours
        skew_angle = cls._estimate_skew_angle(gray)

        # 5. Table presence estimation (horizontal & vertical line detection)
        has_tables = cls._detect_tables(gray)

        return {
            "width": width,
            "height": height,
            "resolution_mp": round((width * height) / 1_000_000, 2),
            "blur_score": round(blur_score, 2),
            "is_blurry": is_blurry,
            "contrast_score": round(contrast_score, 2),
            "is_low_contrast": is_low_contrast,
            "noise_ratio": round(noise_ratio, 2),
            "is_noisy": is_noisy,
            "skew_angle": round(skew_angle, 2),
            "has_tables": has_tables,
            "layout_complexity": "High" if has_tables or (width > 2000 and height > 2000) else "Standard"
        }

    @staticmethod
    def _estimate_skew_angle(gray: np.ndarray) -> float:
        """Estimates rotation skew angle using contour bounding box angles."""
        try:
            # Otsu thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            # Find coordinates of all non-zero pixels
            pts = cv2.findNonZero(thresh)
            if pts is None or len(pts) < 100:
                return 0.0
            rect = cv2.minAreaRect(pts)
            angle = rect[-1]
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
            return float(angle)
        except Exception:
            return 0.0

    @staticmethod
    def _detect_tables(gray: np.ndarray) -> bool:
        """Detects whether horizontal and vertical grid lines form a table structure."""
        try:
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # Horizontal line kernel
            horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
            
            # Vertical line kernel
            vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
            
            table_mask = cv2.add(horiz_lines, vert_lines)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            return len(contours) > 10
        except Exception:
            return False
