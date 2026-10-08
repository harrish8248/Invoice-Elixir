"""
Invoice OCR System - Master Invoice Data Extractor
Orchestrates specialized field extractors to construct a complete InvoiceData structure.
Never invents values for missing fields.
"""

import re
from typing import Dict, Any, List, Tuple
from app.models.invoice_schema import InvoiceData, FieldResult
from app.extraction.gstin_extractor import GSTINExtractor
from app.extraction.date_extractor import DateExtractor
from app.extraction.amount_extractor import AmountExtractor
from app.extraction.line_item_extractor import LineItemExtractor
from app.extraction.regex_patterns import (
    INVOICE_NUM_PATTERNS, PO_NUM_PATTERNS, EMAIL_PATTERN, PHONE_PATTERN, PIN_CODE_PATTERN
)

class InvoiceExtractor:
    """Master extraction orchestrator."""

    @classmethod
    def extract_invoice_data(cls, text: str) -> InvoiceData:
        """Parses full OCR text into structured InvoiceData payload."""
        lines = text.splitlines()

        # 1. GSTIN Extraction (Highest Priority)
        supplier_gstin, buyer_gstin = GSTINExtractor.extract_gstins(text)

        # 2. Date Extraction
        invoice_date, due_date = DateExtractor.extract_dates(text)

        # 3. Financial Amount Extraction
        amounts = AmountExtractor.extract_amounts(text)

        # 4. Line Items Table Extraction
        line_items = LineItemExtractor.extract_line_items(text)

        # 5. Metadata extraction (Invoice Number, PO Number, Email, Phone, Currency)
        invoice_number = cls._extract_invoice_number(text)
        po_number = cls._extract_po_number(text)
        email = cls._extract_email(text)
        phone = cls._extract_phone(text)
        currency = cls._extract_currency(text)

        # 6. Party details (Supplier & Buyer names/addresses)
        supplier_name, buyer_name, supplier_addr, buyer_addr = cls._extract_party_info(text)

        return InvoiceData(
            supplier_gstin=supplier_gstin,
            supplier_name=supplier_name,
            supplier_address=supplier_addr,
            buyer_gstin=buyer_gstin,
            buyer_name=buyer_name,
            buyer_address=buyer_addr,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            po_number=po_number,
            payment_terms=FieldResult(value="Not detected", confidence=0.0, status="Not Detected"),
            contact_email=email,
            contact_phone=phone,
            bank_details=FieldResult(value="Not detected", confidence=0.0, status="Not Detected"),
            currency=currency,
            taxable_amount=amounts["taxable_amount"],
            cgst=amounts["cgst"],
            sgst=amounts["sgst"],
            igst=amounts["igst"],
            subtotal=amounts["subtotal"],
            round_off=amounts["round_off"],
            total_amount=amounts["total_amount"],
            line_items=line_items
        )

    @staticmethod
    def _extract_invoice_number(text: str) -> FieldResult:
        # 1. Direct Regex Patterns
        for pattern in INVOICE_NUM_PATTERNS:
            match = pattern.search(text)
            if match:
                val = match.group(1).strip()
                # Sanity check: ignore false substrings of 'number'
                if val.lower() not in ["ber", "number", "no", "num", "invoice", "date"]:
                    return FieldResult(value=val, raw_value=match.group(0), confidence=92.0, status="Valid")

        # 2. Multi-line contextual scanning
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for idx, line in enumerate(lines):
            line_lower = line.lower()
            if any(k in line_lower for k in ["invoice no", "invoice number", "inv no", "bill no"]):
                # Check next line or colon suffix
                parts = re.split(r"[:\s]+", line)
                for part in parts:
                    clean_p = re.sub(r"[^A-Za-z0-9/\-_]", "", part)
                    if len(clean_p) >= 4 and any(c.isdigit() for c in clean_p) and clean_p.lower() not in ["number", "invoice", "original"]:
                        return FieldResult(value=clean_p, confidence=90.0, status="Valid")
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip(": -")
                    clean_next = re.sub(r"[^A-Za-z0-9/\-_]", "", next_line)
                    if len(clean_next) >= 4 and any(c.isdigit() for c in clean_next):
                        return FieldResult(value=clean_next, confidence=88.0, status="Valid")

        # 3. Alphanumeric identifier fallback (e.g. HY262700002)
        match_id = re.search(r"\b([A-Z]{2,4}\d{6,12})\b", text)
        if match_id:
            return FieldResult(value=match_id.group(1), confidence=85.0, status="Valid")

        return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")


    @staticmethod
    def _extract_po_number(text: str) -> FieldResult:
        for pattern in PO_NUM_PATTERNS:
            match = pattern.search(text)
            if match:
                val = match.group(1).strip()
                return FieldResult(value=val, raw_value=match.group(0), confidence=90.0, status="Valid")
        return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")

    @staticmethod
    def _extract_email(text: str) -> FieldResult:
        match = EMAIL_PATTERN.search(text)
        if match:
            return FieldResult(value=match.group(0), confidence=95.0, status="Valid")
        return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")

    @staticmethod
    def _extract_phone(text: str) -> FieldResult:
        match = PHONE_PATTERN.search(text)
        if match:
            return FieldResult(value=match.group(0), confidence=90.0, status="Valid")
        return FieldResult(value="Not detected", confidence=0.0, status="Not Detected")

    @staticmethod
    def _extract_currency(text: str) -> FieldResult:
        if re.search(r"(?i)\b(INR|Rs\.?|\u20b9|Rupees)\b", text):
            return FieldResult(value="INR", confidence=95.0, status="Valid")
        elif re.search(r"(?i)\b(USD|\$)\b", text):
            return FieldResult(value="USD", confidence=95.0, status="Valid")
        elif re.search(r"(?i)\b(EUR|\u20ac)\b", text):
            return FieldResult(value="EUR", confidence=95.0, status="Valid")
        return FieldResult(value="INR", confidence=70.0, status="Valid", validation_message="Defaulted to INR.")

    @staticmethod
    def _extract_party_info(text: str) -> Tuple[FieldResult, FieldResult, FieldResult, FieldResult]:
        """Parses supplier and buyer entity names and addresses."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        supplier_name = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
        buyer_name = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
        supplier_addr = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")
        buyer_addr = FieldResult(value="Not detected", confidence=0.0, status="Not Detected")

        if lines:
            # Top non-header line is usually Supplier Name
            for l in lines[:5]:
                if not any(k in l.lower() for k in ["tax invoice", "invoice", "original", "bill to", "gstin"]):
                    supplier_name = FieldResult(value=l, confidence=80.0, status="Valid")
                    break

        # Scan for Bill To / Buyer section
        for idx, l in enumerate(lines):
            l_lower = l.lower()
            if any(k in l_lower for k in ["bill to", "billed to", "buyer", "customer"]):
                if idx + 1 < len(lines):
                    buyer_name = FieldResult(value=lines[idx + 1], confidence=85.0, status="Valid")
                if idx + 2 < len(lines):
                    buyer_addr = FieldResult(value=lines[idx + 2], confidence=75.0, status="Valid")
                break

        return supplier_name, buyer_name, supplier_addr, buyer_addr
