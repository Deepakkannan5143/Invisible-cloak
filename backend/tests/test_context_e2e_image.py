"""End-to-end contextual image tests (Tesseract-gated).

Renders realistic synthetic screenshots (bank-payment block, identity block,
split-card layout, negative order-number block) and drives the full
image -> OCR -> DETECT(context) -> LOCATE -> PROTECT -> VERIFY path, asserting
that the correct regions are detected/redacted and that negative-context
layouts are NOT redacted.

Only synthetic/fake identifiers are used. Auto-skips without Tesseract.
"""

import base64
import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.pipeline.ocr import tesseract_available
from app.pipeline.protect import decode_image
from app.pipeline.engine import run_pipeline
from app.schemas import ScanRequest

pytestmark = pytest.mark.skipif(
    not tesseract_available(),
    reason="system Tesseract not installed; see backend/README.md",
)

# Synthetic (fake) identifiers.
VALID_AADHAAR = "4829 1736 4926"       # Verhoeff-valid
LABELLED_AADHAAR = "2345 6789 0123"    # illustrative
VALID_CARD = "5264 1234 5678 0006"     # Luhn-valid

_FONT_CANDIDATES = [
    os.getenv("CLOAK_TEST_FONT", ""),
    "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size=40):
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    pytest.skip("no scalable TrueType font available")


def _render(lines, width=780):
    font = _font()
    height = 60 + 56 * len(lines)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        draw.text((40, 30 + 56 * i), ln, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return b64, width, height


def _scan(lines):
    b64, w, h = _render(lines)
    return run_pipeline(
        ScanRequest(image_base64=b64, image_width=w, image_height=h, mode="frosted")
    )


def _types(resp):
    return {d.type for d in resp.detections}


# --- Bank payment block -----------------------------------------------------

def test_bank_payment_block_redacts_card_cvv_expiry():
    resp = _scan(
        ["Bank Payment", "Debit Card Number", VALID_CARD, "CVV: 482", "Expiry: 09/29"]
    )
    t = _types(resp)
    assert "CREDIT_CARD" in t
    assert "CVV" in t
    assert "CARD_EXPIRY" in t
    # every detection is protected and carries a real pixel bbox
    for d in resp.detections:
        assert d.status == "protected"
        assert d.bbox[2] > 0 and d.bbox[3] > 0
        assert VALID_CARD not in d.text and VALID_CARD.replace(" ", "") not in d.text
    assert resp.protected_image and resp.protected_image.startswith("data:image/png")


# --- Identity block: label above value (spatial context) -------------------

def test_identity_block_label_above_value():
    resp = _scan(["Identity Verification", "Aadhaar Number", LABELLED_AADHAAR])
    assert "AADHAAR" in _types(resp)
    assert resp.summary.total_detections >= 1
    assert resp.summary.protected_count >= 1


# --- Card split across lines ------------------------------------------------

def test_card_split_across_lines_is_reconstructed():
    resp = _scan(["Card Number", "5264 1234", "5678 0006"])
    cards = [d for d in resp.detections if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    assert cards[0].status == "protected"
    # union bbox should span both numeric lines (tall region)
    assert cards[0].bbox[3] > 40


# --- Negative context: order number must NOT be redacted -------------------

def test_order_number_image_not_redacted():
    resp = _scan(["Your Order", "Order Number", "123456789012", "Thank you"])
    assert resp.summary.total_detections == 0
    assert resp.summary.protected_count == 0


def test_invoice_number_image_not_redacted():
    resp = _scan(["Invoice", "Invoice Number", "987654321098"])
    # Should not produce a high-confidence Aadhaar/card detection.
    assert all(d.type not in ("AADHAAR", "CREDIT_CARD") for d in resp.detections)


# --- Values in different areas of the image --------------------------------

def test_multiple_regions_different_areas():
    resp = _scan(
        [
            "Profile", "Aadhaar Number", VALID_AADHAAR,
            "Payment", "Credit Card", VALID_CARD,
        ]
    )
    t = _types(resp)
    assert "AADHAAR" in t and "CREDIT_CARD" in t
    # detections are in vertically distinct areas
    ys = sorted(d.bbox[1] for d in resp.detections if d.type in ("AADHAAR", "CREDIT_CARD"))
    assert ys[-1] - ys[0] > 100


# --- Re-OCR verification actually covers the number ------------------------

def test_reocr_verification_after_context_detection():
    from app.pipeline.detectors import detect_text
    from app.pipeline.locate import Box
    from app.pipeline.ocr import ocr_text_in_region

    resp = _scan(["Bank Payment", "Debit Card Number", VALID_CARD])
    protected = decode_image(resp.protected_image)
    for d in resp.detections:
        if d.type != "CREDIT_CARD":
            continue
        box = Box(d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3])
        recovered = ocr_text_in_region(protected, box)
        assert len(detect_text(recovered, {"CREDIT_CARD"})) == 0
        assert d.verification_passed is True
