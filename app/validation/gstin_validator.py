"""
Invoice OCR System - GSTIN Validation Module
Implements structural and Modulo-36 Checksum verification for GSTIN numbers.
"""

from typing import Dict, Any

class GSTINValidator:
    """Validates GSTIN format and checksum according to official GST specification."""

    @classmethod
    def validate_gstin(cls, gstin: str) -> Dict[str, Any]:
        """
        Validates GSTIN string.
        Returns result dictionary containing validity boolean, state code, PAN component, and checksum status.
        """
        if not gstin or gstin == "Not detected":
            return {
                "valid": False,
                "status": "Not Detected",
                "message": "GSTIN is missing."
            }

        gstin = gstin.strip().upper()
        if len(gstin) != 15:
            return {
                "valid": False,
                "status": "Invalid Length",
                "message": f"GSTIN must be exactly 15 characters, received {len(gstin)}."
            }

        state_code = gstin[:2]
        pan = gstin[2:12]
        entity_num = gstin[12]
        z_char = gstin[13]
        check_digit = gstin[14]

        if z_char != "Z":
            return {
                "valid": False,
                "status": "Format Error",
                "message": f"14th character of GSTIN must be 'Z', received '{z_char}'."
            }

        # Perform mod-36 checksum verification
        checksum_valid = cls._verify_mod36_checksum(gstin)

        return {
            "valid": checksum_valid,
            "status": "Valid" if checksum_valid else "Checksum Warning",
            "state_code": state_code,
            "pan": pan,
            "checksum_valid": checksum_valid,
            "message": "GSTIN verified successfully." if checksum_valid else "Checksum calculation mismatched."
        }

    @staticmethod
    def _verify_mod36_checksum(gstin: str) -> bool:
        """Calculates Modulo 36 checksum for 15-character GSTIN."""
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        char_map = {c: i for i, c in enumerate(chars)}

        factor = 1
        total = 0
        mod = 36

        for i in range(14):
            c = gstin[i]
            if c not in char_map:
                return False
            val = char_map[c] * factor
            factor = 2 if factor == 1 else 1
            val = (val // mod) + (val % mod)
            total += val

        remainder = total % mod
        check_code = (mod - remainder) % mod
        expected_check_char = chars[check_code]

        return gstin[14] == expected_check_char
