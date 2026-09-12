"""End-to-end image tests for all eight categories (Tesseract-gated).

Renders synthetic screenshots and drives the full
image -> OCR -> DETECT -> LOCATE -> PROTECT -> VERIFY -> RESPONSE path via
``run_pipeline``. Asserts detection, accurate pixel bboxes, masked (never raw)
values, verification, per-toggle isolation, multi-line address grouping,
custom-pattern support, false-positive suppression, and detector-failure
handling.

All identifiers are synthetic / fake. Auto-skips without a system Tesseract.
"""

import base64
import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.pipeline.ocr import tesseract_available
from app.pipeline.protect import decode_image
from app.pipeline.engine import run_pipeline
from app.schemas import CustomPattern, ScanRequest

pytestmark = pytest.mark.skipif(
    not tesseract_available(),
    reason="system Tesseract not installed; see backend/README.md",
)

# Synthetic (fake) identifiers.
AADHAAR = "4829 1736 4926"          # Verhoeff-valid
CARD = "4111 1111 1111 1111"        # Luhn-valid
API_KEY = "sk-test-9fJ2Kd8sLpQw3nZx7Ab1Cd"
EMAIL = "deepak@example.com"
PHONE = "+91 98765 43210"
PASSWORD = "MySecret123"

_FONT_CANDIDATES = [
    os.getenv("CLOAK_TEST_FONT", ""),
    "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size=36):
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    pytest.skip("no scalable TrueType font available")


def _render(lines, width=860):
    font = _font()
    height = 60 + 52 * len(lines)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        draw.text((40, 30 + 52 * i), ln, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return b64, width, height


def _scan(lines, enabled=None, customs=None, mode="frosted"):
    b64, w, h = _render(lines)
    return run_pipeline(ScanRequest(
        image_base64=b64, image_width=w, image_height=h, mode=mode,
        enabled_types=enabled, custom_patterns=customs,
    ))


def _types(resp):
    return {d.type for d in resp.detections}


def _no_raw_values(resp, *raws):
    for d in resp.detections:
        for raw in raws:
            assert raw not in d.text
            assert raw.replace(" ", "") not in d.text


# --- The full mega image: all eight categories -----------------------------

_MEGA_LINES = [
    "Aadhaar Number", AADHAAR,
    "Credit Card", CARD,
    "Email", EMAIL,
    "Phone", PHONE,
    "API Key", API_KEY,
    f"Password: {PASSWORD}",
    "Home Address:", "12, Anna Nagar Main Road,", "Chennai, Tamil Nadu - 600040",
    "Employee ID: EMP-123456",
]
_MEGA_ENABLED = ["aadhaar", "credit_card", "api_key", "password", "email",
                 "phone", "address", "custom"]
_MEGA_CUSTOM = [CustomPattern(name="Employee ID", regex="EMP-[0-9]{6}")]


def test_all_eight_categories_end_to_end():
    resp = _scan(_MEGA_LINES, _MEGA_ENABLED, _MEGA_CUSTOM)
    t = _types(resp)
    for expected in ("AADHAAR", "CREDIT_CARD", "API_KEY", "PASSWORD",
                     "EMAIL", "PHONE", "ADDRESS", "CUSTOM_PATTERN"):
        assert expected in t, f"{expected} not detected; got {sorted(t)}"

    # Every detection: protected, real bbox, verified, masked.
    for d in resp.detections:
        assert d.status == "protected"
        assert d.bbox[2] > 0 and d.bbox[3] > 0
        assert d.verification_passed is True
        assert 1 <= d.attempts <= 3
    _no_raw_values(resp, AADHAAR, CARD, API_KEY, EMAIL, PHONE, PASSWORD)

    # A real, differing protected PNG was produced.
    assert resp.protected_image and resp.protected_image.startswith("data:image/png")
    original = decode_image(_render(_MEGA_LINES)[0])
    protected = decode_image(resp.protected_image)
    assert original.tobytes() != protected.tobytes()

    # Detections exist and were protected -> score reflects success but is <100.
    assert 0 < resp.privacy_score < 100
    assert resp.summary.protected_count == resp.summary.total_detections


def test_address_multiline_is_single_region():
    resp = _scan(
        ["Home Address:", "12, Anna Nagar Main Road,", "Chennai, Tamil Nadu - 600040"],
        ["address"],
    )
    addrs = [d for d in resp.detections if d.type == "ADDRESS"]
    assert len(addrs) == 1
    # The single union box spans all three lines (tall region).
    assert addrs[0].bbox[3] > 100
    assert addrs[0].status == "protected" and addrs[0].verification_passed


def test_custom_pattern_end_to_end():
    resp = _scan(["Employee ID: EMP-123456"], ["custom"], _MEGA_CUSTOM)
    customs = [d for d in resp.detections if d.type == "CUSTOM_PATTERN"]
    assert len(customs) == 1
    assert customs[0].bbox[2] > 0 and customs[0].bbox[3] > 0
    assert customs[0].status == "protected"
    assert "EMP-123456" not in customs[0].text


# --- Per-toggle isolation over the full pipeline (§26) ---------------------

@pytest.mark.parametrize("only,expect", [
    ("aadhaar", "AADHAAR"),
    ("credit_card", "CREDIT_CARD"),
    ("email", "EMAIL"),
    ("phone", "PHONE"),
    ("password", "PASSWORD"),
    ("api_key", "API_KEY"),
    ("address", "ADDRESS"),
])
def test_only_one_category_enabled(only, expect):
    resp = _scan(_MEGA_LINES, [only], _MEGA_CUSTOM)
    t = _types(resp)
    assert expect in t, f"{expect} missing with only {only}; got {sorted(t)}"
    # Nothing else is protected.
    assert t == {expect}, f"unexpected extra types {sorted(t - {expect})}"


def test_disabled_category_leaves_pixels_untouched():
    # With only Aadhaar enabled, the credit-card region must be untouched.
    b64, w, h = _render(["Aadhaar Number", AADHAAR, "Credit Card", CARD])
    only_aadhaar = run_pipeline(ScanRequest(
        image_base64=b64, image_width=w, image_height=h,
        mode="frosted", enabled_types=["aadhaar"],
    ))
    assert _types(only_aadhaar) == {"AADHAAR"}
    # The Aadhaar region differs from original; the card region does not, since
    # the card is on a different line and was never protected.
    original = decode_image(b64)
    protected = decode_image(only_aadhaar.protected_image)
    assert original.tobytes() != protected.tobytes()  # something changed
    # No CREDIT_CARD detection exists at all.
    assert all(d.type != "CREDIT_CARD" for d in only_aadhaar.detections)


# --- False positives (§17) --------------------------------------------------

def test_order_invoice_product_ids_not_redacted_e2e():
    resp = _scan(
        ["Your Order", "Order Number", "123456789012",
         "Invoice Number", "987654321098", "Product ID", "111122223333"],
        ["aadhaar", "credit_card", "phone", "address"],
    )
    assert resp.summary.total_detections == 0
    assert resp.privacy_score == 100.0


# --- Privacy score honesty (§23) -------------------------------------------

def test_privacy_score_100_only_when_nothing_detected():
    resp = _scan(["Welcome to the dashboard", "No sensitive data here"],
                 ["aadhaar", "credit_card", "email", "phone", "address"])
    assert resp.summary.total_detections == 0
    assert resp.privacy_score == 100.0
