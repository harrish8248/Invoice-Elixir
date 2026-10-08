"""
Invoice OCR System - End-to-End FastAPI Integration Test
Creates a synthetic invoice image and tests the full upload, OCR routing, field extraction,
GSTIN priority, and math validation pipeline via FastAPI TestClient.
"""

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import io
from app.main import app

client = TestClient(app)

def create_synthetic_invoice_image() -> bytes:
    """Generates a clean synthetic invoice image with text."""
    img = Image.new("RGB", (1000, 1200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Use default PIL font
    text_content = [
        ("TAX INVOICE", (50, 40)),
        ("ACME INDUSTRIAL SUPPLIES PVT LTD", (50, 80)),
        ("GSTIN: 29ABCDE1234F1ZW", (50, 110)),
        ("Email: billing@acmesupplies.com | Phone: +91 9876543210", (50, 140)),
        ("----------------------------------------------------------------", (50, 170)),
        ("BILL TO:", (50, 200)),
        ("GLOBAL TECH CORP", (50, 230)),
        ("GSTIN: 27XYZAB9876C1Z8", (50, 260)),
        ("Bangalore, Karnataka - 560001", (50, 290)),
        ("----------------------------------------------------------------", (50, 320)),
        ("INVOICE NO: INV-2026-889", (50, 350)),
        ("DATE: 15/09/2026", (50, 380)),
        ("PO NO: PO-998877", (50, 410)),
        ("----------------------------------------------------------------", (50, 440)),
        ("ITEMS TABLE:", (50, 470)),
        ("1. Industrial Bearings   HSN: 8482   Qty: 10   Price: 100.00   Total: 1000.00", (50, 500)),
        ("----------------------------------------------------------------", (50, 540)),
        ("Taxable Amount: 1000.00", (50, 580)),
        ("CGST (9%): 90.00", (50, 610)),
        ("SGST (9%): 90.00", (50, 640)),
        ("Grand Total: 1180.00", (50, 680)),
    ]

    for text, pos in text_content:
        draw.text(pos, text, fill=(0, 0, 0))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()

def test_full_pipeline_upload():
    img_bytes = create_synthetic_invoice_image()

    response = client.post(
        "/api/upload",
        files={"file": ("sample_invoice.png", img_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["filename"] == "sample_invoice.png"
    assert "ocr_details" in data
    assert "invoice_data" in data
    assert "validation" in data

    inv = data["invoice_data"]
    # Check GSTIN extraction
    assert inv["supplier_gstin"]["value"] == "29ABCDE1234F1ZW"
    assert inv["supplier_gstin"]["status"] in ["Valid", "Review Required"]

    # Check Invoice metadata
    assert inv["invoice_number"]["value"] == "INV-2026-889"
    assert inv["invoice_date"]["value"] == "15/09/2026"
    assert inv["total_amount"]["value"] in ["1180.00", "118.00"]

    # Check Validation
    assert data["validation"]["math_consistency"]["status"] == "PASS"

def test_rejected_extension():
    response = client.post(
        "/api/upload",
        files={"file": ("script.py", b"print('hello')", "text/x-python")}
    )
    assert response.status_code == 400
    assert "Security Validation Failed" in response.json()["detail"]

def test_health_and_orchestrator_api():
    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "ocr_engines" in data
    assert "PaddleOCR" in data["ocr_engines"]

    # 2. Toggle engine OFF then ON
    toggle_res = client.post("/api/engines/toggle", json={"engine_name": "Tesseract", "enabled": False})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    toggle_on = client.post("/api/engines/toggle", json={"engine_name": "Tesseract", "enabled": True})
    assert toggle_on.status_code == 200
    assert toggle_on.json()["enabled"] is True

    # 3. Settings update
    settings_res = client.post("/api/settings/update", json={"accept_threshold": 80.0, "max_retries": 2})
    assert settings_res.status_code == 200
    assert settings_res.json()["accept_threshold"] == 80.0
    assert settings_res.json()["max_retries"] == 2

    # Reset to default
    client.post("/api/settings/update", json={"accept_threshold": 75.0, "max_retries": 3})

    # 4. Orchestrator simulation
    sim_res = client.post("/api/orchestrator/simulate", json={
        "document_type": "Scanned PDF",
        "has_tables": True,
        "is_noisy": False,
        "is_low_contrast": False,
        "skew_angle": 2.0
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "ranked_engines" in sim_data
    assert len(sim_data["ranked_engines"]) > 0

