"""
Invoice OCR Processing System - Configuration Module
Provides centralized, configurable parameters for file intake, security, PDF inspection,
preprocessing, OCR engine routing, quality thresholds, and validation rules.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

# Ensure runtime directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Security & Intake Configuration
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # Strict < 15 MB limit requirement
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/x-png"
}

# Magic numbers/file signatures for strict intake verification
FILE_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"]
}

# Tesseract executable configuration for Windows host
TESSERACT_CMD_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD", TESSERACT_CMD_DEFAULT)

# OCR Quality & Router Thresholds
OCR_ACCEPT_THRESHOLD = float(os.getenv("OCR_ACCEPT_THRESHOLD", "75.0"))
MAX_OCR_RETRIES = int(os.getenv("MAX_OCR_RETRIES", "3"))

# Preprocessing Settings
PREPROCESSING_CONFIG = {
    "target_dpi": 300,
    "max_dimension": 3000,
    "contrast_clip_limit": 2.0,
    "tile_grid_size": (8, 8),
    "deskew_max_angle": 15.0,
    "denoise_h": 10
}

# OCR Engine Configurations & Capability Weights
# Configurable without code rewrite
OCR_ENGINE_CONFIG = {
    "PaddleOCR": {
        "enabled": True,
        "priority": 1,
        "strengths": ["scanned", "multi_column", "tables", "mixed"],
        "weight_digital": 0.85,
        "weight_scanned": 0.95
    },
    "Surya": {
        "enabled": True,
        "priority": 2,
        "strengths": ["complex_layout", "scanned", "tables", "multi_language"],
        "weight_digital": 0.88,
        "weight_scanned": 0.92
    },
    "Tesseract": {
        "enabled": True,
        "priority": 3,
        "strengths": ["digital_pdf", "clean_image", "standard_text"],
        "weight_digital": 0.90,
        "weight_scanned": 0.75
    },
    "docTR": {
        "enabled": True,
        "priority": 4,
        "strengths": ["complex_layout", "handwriting", "field_detection"],
        "weight_digital": 0.85,
        "weight_scanned": 0.85
    },
    "EasyOCR": {
        "enabled": True,
        "priority": 5,
        "strengths": ["noisy_image", "curved_text", "scene_text"],
        "weight_digital": 0.80,
        "weight_scanned": 0.80
    }
}

# Extraction & Validation Rules
GSTIN_REGEX = r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b"
AMOUNT_TOLERANCE_PERCENT = 1.0  # 1% allowable rounding tolerance for tax calculation validation
