"""End-to-end OCR integration test.

Proves the full IMAGE -> OCR -> reconstruct -> DETECT -> LOCATE -> PROTECT ->
VERIFY -> RESPONSE path using ONLY synthetic/fake identifiers rendered onto a
canvas. Split number tokens (``7730`` ``0889`` ``2163``) must be reconstructed
and detected as AADHAAR; (``9186`` ``7890`` ``6417`` ``0314``) as a Luhn-valid
CREDIT_CARD.

Skips automatically when Tesseract is not installed, so the rest of the suite
still runs on machines without the system binary.
"""

import base64
import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.pipeline.ocr import tesseract_available
from app.pipeline.engine import run_pipeline
from app.schemas import ScanRequest

pytestmark = pytest.mark.skipif(
    not tesseract_available(),
    reason="system Tesseract not installed; see backend/README.md",
)

# Synthetic (fake) test identifiers only.
FAKE_AADHAAR = "7730 0889 2163"
FAKE_CARD = "9186 7890 6417 0314"

# Candidate TrueType fonts; the first that exists is used. A crisp, reasonably
# large font is what makes OCR reliable.
_FONT_CANDIDATES = [
    os.getenv("CLOAK_TEST_FONT", ""),
    "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Last resort: fc-match via PIL's default TTF discovery.
    try:
        return ImageFont.truetype("NotoSans-Regular.ttf", size)
    except Exception:
        pytest.skip("no scalable TrueType font available to render the test image")


def _synthetic_image() -> tuple[str, int, int]:
    w, h = 900, 360
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = _load_font(48)
    draw.text((40, 50), f"Aadhaar {FAKE_AADHAAR}", fill=(0, 0, 0), font=font)
    draw.text((40, 190), f"Card {FAKE_CARD}", fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return b64, w, h


def test_ocr_end_to_end_detects_split_numbers():
    b64, w, h = _synthetic_image()
    resp = run_pipeline(
        ScanRequest(image_base64=b64, image_width=w, image_height=h, mode="frosted")
    )

    # Core acceptance: detections must be > 0 (the original bug returned 0).
    assert resp.success is True
    assert resp.summary.total_detections > 0
    assert resp.summary.protected_count > 0

    types = {d.type for d in resp.detections}
    # OCR should reconstruct both split values.
    assert "AADHAAR" in types
    assert "CREDIT_CARD" in types

    for d in resp.detections:
        # Raw values must never be returned.
        assert FAKE_AADHAAR not in d.text
        assert FAKE_CARD not in d.text
        assert FAKE_CARD.replace(" ", "") not in d.text
        # Every detection carries a real pixel-space union bbox.
        assert len(d.bbox) == 4 and d.bbox[2] > 0 and d.bbox[3] > 0
        assert d.status == "protected"
        assert 1 <= d.attempts <= 3

    # A genuinely redacted PNG is returned.
    assert resp.protected_image and resp.protected_image.startswith("data:image/png")


def test_ocr_card_is_luhn_validated():
    # The fake card must actually pass Luhn so it is classified as CREDIT_CARD.
    from app.pipeline.validators import luhn_check

    assert luhn_check(FAKE_CARD)


def test_reocr_verification_covers_the_number():
    """After protection, re-OCR of the card region must no longer read the card."""
    from app.pipeline.ocr import ocr_text_in_region
    from app.pipeline.protect import decode_image
    from app.pipeline.detectors import detect_text

    b64, w, h = _synthetic_image()
    resp = run_pipeline(
        ScanRequest(image_base64=b64, image_width=w, image_height=h, mode="frosted")
    )
    protected = decode_image(resp.protected_image)

    for d in resp.detections:
        from app.pipeline.locate import Box, LocatedDetection

        box = Box(d.bbox[0], d.bbox[1], d.bbox[2], d.bbox[3])
        recovered = ocr_text_in_region(protected, box)
        # No sensitive token of this type should survive in the recovered text.
        assert len(detect_text(recovered, {d.type})) == 0
        assert d.verification_passed is True
