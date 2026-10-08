"""
Invoice OCR System - Regex Patterns Registry
Compiled regular expressions for field extraction & candidate matching.
"""

import re

# GSTIN Regex: 2 digits (state code) + 5 letters (PAN) + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric
GSTIN_PATTERN = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[A-Z0-9]{1}[0-9A-Z]{1})\b")

# Multi-format Date Regex (DD/MM/YYYY, YYYY-MM-DD, DD-MMM-YYYY)
DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
    re.compile(r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"),
    re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b", re.IGNORECASE)
]

# Invoice Number Patterns (strict word boundary to avoid capturing parts of 'Number')
INVOICE_NUM_PATTERNS = [
    re.compile(r"(?i)\b(?:Invoice|Inv|Bill)\s*(?:Number|Num|No\.?|\#)\b\s*[:\.-]?\s*([A-Za-z0-9][A-Za-z0-9/\-_]{2,30})"),
    re.compile(r"(?i)\b(?:Invoice|Inv)\s*#\s*[:\.-]?\s*([A-Za-z0-9][A-Za-z0-9/\-_]{2,30})"),
    re.compile(r"(?i)\b(?:Invoice|Inv|Bill)\s*(?:Number|Num|No\.?)\s*[:\.-]\s*([A-Za-z0-9][A-Za-z0-9/\-_]{2,30})")
]

# PO Number Patterns
PO_NUM_PATTERNS = [
    re.compile(r"(?i)\b(?:PO|P\.O\.|Purchase\s+Order)\s*(?:Number|Num|No\.?|\#)?\b\s*[:\.-]?\s*([A-Za-z0-9][A-Za-z0-9/\-_]{2,30})")
]


# HSN / SAC Code Pattern (4, 6, or 8 digits)
HSN_SAC_PATTERN = re.compile(r"\b(\d{4}|\d{6}|\d{8})\b")

# Email Address Pattern
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Phone Number Pattern
PHONE_PATTERN = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")

# Indian PIN Code Pattern (6 digits starting with 1-9)
PIN_CODE_PATTERN = re.compile(r"\b[1-9][0-9]{5}\b")

# Monetary Amount Patterns (matches numbers like 1,234.56 or 12345.00)
AMOUNT_PATTERN = re.compile(r"(?:Rs\.?|INR|\u20b9)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)")
