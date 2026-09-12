"""End-to-end payment-screenshot test (Tesseract-gated).

Renders the payment layout from the debugging spec and drives the full
image -> Tesseract -> DETECT -> LOCATE -> PROTECT -> VERIFY path, asserting the
card number is detected + protected, CVV is only flagged with card context, and
the protected image actually differs from the original (real redaction).

Synthetic/fake identifiers only. Auto-skips without Tesseract.
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

CARD = "4111 1111 1111 1111"  # Luhn-valid, fake

_FONT_CANDIDATES = [
    os.getenv("CLOAK_TEST_FONT", ""),
    "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size=38):
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    pytest.skip("no scalable TrueType font available")


def _render(lines, width=760):
    font = _font()
    img = Image.new("RGB", (width, 60 + 50 * len(lines)), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        draw.text((40, 30 + 50 * i), ln, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return b64, img.width, img.height


def test_payment_details_screenshot_end_to_end():
    b64, w, h = _render(
        ["PAYMENT DETAILS", "", "Credit Card", CARD, "", "CVV", "482", "", "Expiry", "09/29"]
    )
    resp = run_pipeline(
        ScanRequest(image_base64=b64, image_width=w, image_height=h, mode="frosted")
    )

    types = {d.type for d in resp.detections}
    # At least the card must be detected and protected.
    assert "CREDIT_CARD" in types
    assert resp.summary.protected_count >= 1

    for d in resp.detections:
        assert d.status == "protected"
        assert d.bbox[2] > 0 and d.bbox[3] > 0
        # Raw values never returned.
        assert CARD not in d.text and CARD.replace(" ", "") not in d.text
        # If CVV/expiry are flagged they must have contextual evidence (they are
        # only produced by the label-anchored, card-context path).
        if d.type in ("CVV", "CARD_EXPIRY"):
            assert d.confidence > 0

    # The protected PNG must actually differ from the original (real redaction).
    original = decode_image(b64)
    protected = decode_image(resp.protected_image)
    assert original.tobytes() != protected.tobytes()


def test_payment_card_region_reocr_verified():
    from app.pipeline.detectors import detect_text
    from app.pipeline.locate import Box
    from app.pipeline.ocr import ocr_text_in_region

    b64, w, h = _render(["Credit Card", CARD])
    resp = run_pipeline(
        ScanRequest(image_base64=b64, image_width=w, image_height=h, mode="frosted")
    )
    protected = decode_image(resp.protected_image)
    cards = [d for d in resp.detections if d.type == "CREDIT_CARD"]
    assert cards, "card should be detected"
    for d in cards:
        box = Box(d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3])
        recovered = ocr_text_in_region(protected, box)
        # Re-OCR of the masked region must no longer read a card.
        assert len(detect_text(recovered, {"CREDIT_CARD"})) == 0
        assert d.verification_passed is True
