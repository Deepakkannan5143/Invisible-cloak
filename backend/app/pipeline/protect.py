"""PROTECT stage: masked text placeholders + adaptive image obfuscation.

Never surfaces raw values. Chooses obfuscation strength from severity:

    critical -> frosted glass over deep blur (or heavy pixelation)
    high     -> strong gaussian blur / pixelation
    medium   -> moderate blur
    low      -> light blur

Image redaction uses Pillow so a genuinely protected PNG can be returned.
"""

from __future__ import annotations

import base64
import io
import re

from PIL import Image, ImageDraw, ImageFilter

from .locate import Box, LocatedDetection

# ---------------------------------------------------------------------------
# Masking (text placeholders shown in the report)
# ---------------------------------------------------------------------------

def mask_value(dtype: str, raw: str) -> str:
    """Return a masked placeholder that preserves shape but hides the value."""
    digits = re.sub(r"\D", "", raw)
    if dtype in ("CREDIT_CARD", "DEBIT_CARD"):
        return "XXXX XXXX XXXX " + (digits[-4:] if len(digits) >= 4 else "XXXX")
    if dtype == "AADHAAR":
        return "XXXX XXXX " + (digits[-4:] if len(digits) >= 4 else "XXXX")
    if dtype == "SSN":
        return "XXX-XX-" + (digits[-4:] if len(digits) >= 4 else "XXXX")
    if dtype == "PHONE":
        return "+•• •••••" + (digits[-4:] if len(digits) >= 4 else "••••")
    if dtype == "EMAIL":
        user, _, host = raw.partition("@")
        h = host[:1] if host else "•"
        return (user[:1] or "•") + "•••@" + h + "••.•••"
    if dtype in ("API_KEY", "AWS_ACCESS_KEY"):
        return (raw[:3] if len(raw) >= 3 else raw) + "-••••••••••••"
    if dtype == "ACCESS_TOKEN":
        return (raw[:4] if len(raw) >= 4 else raw) + "••••••••••••"
    if dtype == "JWT_TOKEN":
        return "eyJ••••.••••••.••••"
    if dtype == "PRIVATE_KEY":
        return "-----BEGIN PRIVATE KEY----- ••••"
    if dtype == "PASSWORD":
        return "•" * min(12, max(8, len(raw)))
    if dtype == "CVV":
        # Never reveal any CVV digit.
        return "•" * max(3, len(digits) or 3)
    if dtype == "CARD_EXPIRY":
        return "••/••"
    if dtype in ("IP_ADDRESS", "MAC_ADDRESS"):
        return "•••.•••.•.•"
    if dtype == "PAN":
        return raw[:2] + "•••••" + (raw[-1:] if raw else "•")
    if dtype in ("IBAN", "SWIFT_BIC", "IFSC", "UPI_ID", "CRYPTO_WALLET"):
        return raw[:2] + "•" * 8 + (raw[-2:] if len(raw) >= 2 else "")
    if dtype == "ADDRESS":
        first = raw.split(",")[0].split(" ")[0] if raw else "•••"
        return first + " •••••••, •••"
    return "[REDACTED]"


# ---------------------------------------------------------------------------
# Image obfuscation
# ---------------------------------------------------------------------------

def _blur_region(img: Image.Image, box: Box, radius: float) -> None:
    x1, y1 = int(box.x), int(box.y)
    x2, y2 = int(box.x + box.w), int(box.y + box.h)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.width, x2), min(img.height, y2)
    if x2 <= x1 or y2 <= y1:
        return
    region = img.crop((x1, y1, x2, y2))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=radius))
    img.paste(blurred, (x1, y1))


def _pixelate_region(img: Image.Image, box: Box, blocks: int = 6) -> None:
    x1, y1 = max(0, int(box.x)), max(0, int(box.y))
    x2 = min(img.width, int(box.x + box.w))
    y2 = min(img.height, int(box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return
    region = img.crop((x1, y1, x2, y2))
    w, h = region.size
    small = region.resize(
        (max(1, blocks), max(1, int(blocks * h / max(1, w)))), Image.BILINEAR
    )
    region = small.resize((w, h), Image.NEAREST)
    img.paste(region, (x1, y1))


def _frost_region(img: Image.Image, box: Box) -> None:
    # Heavy blur, then a translucent white "glass" overlay.
    _blur_region(img, box, radius=14)
    x1, y1 = max(0, int(box.x)), max(0, int(box.y))
    x2 = min(img.width, int(box.x + box.w))
    y2 = min(img.height, int(box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return
    overlay = Image.new("RGBA", (x2 - x1, y2 - y1), (255, 255, 255, 90))
    base = img.crop((x1, y1, x2, y2)).convert("RGBA")
    img.paste(Image.alpha_composite(base, overlay).convert(img.mode), (x1, y1))


def _redact_region(img: Image.Image, box: Box) -> None:
    _blur_region(img, box, radius=12)
    x1, y1 = max(0, int(box.x)), max(0, int(box.y))
    x2 = min(img.width, int(box.x + box.w))
    y2 = min(img.height, int(box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return
    draw = ImageDraw.Draw(img)
    draw.rectangle([x1, y1, x2, y2], fill=(17, 24, 39))


# Strength multipliers per severity and per escalation attempt.
_SEVERITY_BLUR = {"low": 8.0, "medium": 12.0, "high": 18.0, "critical": 24.0}


def apply_protection(img: Image.Image, det: LocatedDetection, mode: str,
                     attempt: int = 1) -> None:
    """Obfuscate one detection's region in-place, honoring mode & severity.

    ``attempt`` (>=1) escalates strength for the VERIFY re-pass.
    """
    box = det.box
    escalate = 1.0 + 0.6 * (attempt - 1)  # 1.0, 1.6, 2.2 ...

    # Critical always gets the heaviest treatment regardless of requested mode.
    if det.severity == "critical" or mode == "frosted":
        _frost_region(img, box)
        if det.severity == "critical" and attempt > 1:
            _pixelate_region(img, box, blocks=max(2, int(6 / escalate)))
        return
    if mode == "redact":
        _redact_region(img, box)
        return
    if mode == "pixelate":
        _pixelate_region(img, box, blocks=max(2, int(6 / escalate)))
        return
    # default: blur, scaled by severity and attempt
    radius = _SEVERITY_BLUR.get(det.severity, 12.0) * escalate
    _blur_region(img, box, radius=radius)


# ---------------------------------------------------------------------------
# base64 <-> PIL helpers
# ---------------------------------------------------------------------------

_DATA_URL_RE = re.compile(r"^data:image/[a-zA-Z0-9.+-]+;base64,")


def decode_image(image_base64: str) -> Image.Image:
    payload = _DATA_URL_RE.sub("", image_base64.strip())
    raw = base64.b64decode(payload)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def encode_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return "data:image/png;base64," + b64
