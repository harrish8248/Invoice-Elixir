"""
Invoice OCR Processing System - Base OCR Engine Interface
Defines the standard abstract base class for OCR engine implementations and
unified OCR execution result structure.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

class OCRWordBox(BaseModel):
    """Represents a recognized word/text box with bounding coordinates and confidence."""
    text: str
    confidence: float = Field(ge=0.0, le=100.0)
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2] or polygon coordinates


class OCRResult(BaseModel):
    """Standardized OCR output returned by all OCR engine implementations."""
    engine_name: str
    full_text: str
    confidence: float = Field(ge=0.0, le=100.0)
    words: List[OCRWordBox] = Field(default_factory=list)
    raw_output: Optional[Any] = None
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    is_available: bool = True


class BaseOCREngine(ABC):
    """Abstract Base Class for OCR engine plugins."""

    def __init__(self, name: str):
        self.name = name
        self.available, self.init_error = self.check_availability()

    @abstractmethod
    def check_availability(self) -> tuple[bool, Optional[str]]:
        """
        Checks if required binary/libraries are installed and operational.
        Returns (is_available, error_description_if_unavailable).
        """
        pass

    @abstractmethod
    def process_image(self, image_path: Path) -> OCRResult:
        """
        Executes OCR on an image and returns standardized OCRResult.
        Must handle exceptions gracefully and populate OCRResult error_message if failed.
        """
        pass
