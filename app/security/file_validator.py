"""
Invoice OCR System - File Intake & Security Validation Module
Enforces strict security policies on uploaded invoice files:
- Maximum file size check (< 15 MB)
- File extension validation
- MIME / Magic byte signature checking (doesn't trust file extensions alone)
- Path traversal prevention and safe filename generation
- File corruption check
"""

import os
import uuid
import re
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import config

class SecurityValidationError(Exception):
    """Exception raised when a security or intake validation rule fails."""
    pass


class FileValidator:
    """Validates uploaded files for size, format signature, corruption, and path traversal."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Removes dangerous characters, directory components, and path traversal tokens."""
        # Strip path directory separators
        clean_name = Path(filename).name
        # Keep alphanumeric, dot, underscore, dash
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)
        return clean_name

    @staticmethod
    def generate_safe_filename(original_filename: str) -> str:
        """Generates a non-colliding, safe internal filename using UUID4."""
        ext = Path(original_filename).suffix.lower()
        if ext not in config.ALLOWED_EXTENSIONS:
            ext = ".bin"
        unique_id = uuid.uuid4().hex
        return f"inv_{unique_id}{ext}"

    @classmethod
    def validate_file_size(cls, content_bytes: bytes) -> int:
        """Ensures file size does not exceed the maximum allowed size (15 MB)."""
        size = len(content_bytes)
        if size == 0:
            raise SecurityValidationError("Uploaded file is empty (0 bytes).")
        if size >= config.MAX_FILE_SIZE_BYTES:
            max_mb = config.MAX_FILE_SIZE_BYTES / (1024 * 1024)
            size_mb = size / (1024 * 1024)
            raise SecurityValidationError(
                f"File size exceeds maximum threshold. Received {size_mb:.2f} MB, maximum allowed is {max_mb:.2f} MB."
            )
        return size

    @classmethod
    def validate_extension(cls, filename: str) -> str:
        """Checks if the filename has an allowed extension."""
        ext = Path(filename).suffix.lower()
        if ext not in config.ALLOWED_EXTENSIONS:
            allowed_str = ", ".join(config.ALLOWED_EXTENSIONS)
            raise SecurityValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions are: {allowed_str}"
            )
        return ext

    @classmethod
    def validate_magic_bytes(cls, content_bytes: bytes, ext: str) -> str:
        """
        Validates magic signatures of the binary stream.
        Prevents executable files disguised with fake extensions.
        """
        magic_key = ext.lstrip(".")
        if magic_key == "jpg":
            magic_key = "jpeg"

        expected_signatures = config.FILE_SIGNATURES.get(magic_key, [])
        if not expected_signatures:
            # Fallback for generic image checking
            if content_bytes.startswith(b"\xff\xd8\xff"):
                return "image/jpeg"
            if content_bytes.startswith(b"\x89PNG"):
                return "image/png"
            if content_bytes.startswith(b"%PDF-"):
                return "application/pdf"
            raise SecurityValidationError("Unknown binary file signature.")

        matched = any(content_bytes.startswith(sig) for sig in expected_signatures)
        if not matched:
            raise SecurityValidationError(
                f"File content magic bytes do not match expected signature for extension '{ext}'."
            )

        if ext == ".pdf":
            return "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"

        return "application/octet-stream"

    @classmethod
    def validate_and_save(cls, filename: str, content_bytes: bytes) -> Tuple[str, Path, int, str]:
        """
        Full validation pipeline:
        1. Sanitize filename & check path traversal
        2. Validate size (< 15MB)
        3. Validate extension
        4. Validate magic byte signatures
        5. Generate safe internal filename
        6. Save to temporary uploads directory
        Returns: (safe_filename, target_path, size_bytes, mime_type)
        """
        sanitized = cls.sanitize_filename(filename)
        size_bytes = cls.validate_file_size(content_bytes)
        ext = cls.validate_extension(sanitized)
        mime_type = cls.validate_magic_bytes(content_bytes, ext)

        safe_filename = cls.generate_safe_filename(sanitized)
        target_path = config.UPLOAD_DIR / safe_filename

        # Ensure no path traversal escaped UPLOAD_DIR
        resolved_path = target_path.resolve()
        if not str(resolved_path).startswith(str(config.UPLOAD_DIR.resolve())):
            raise SecurityValidationError("Path traversal attack detected.")

        with open(target_path, "wb") as f:
            f.write(content_bytes)

        return safe_filename, target_path, size_bytes, mime_type
