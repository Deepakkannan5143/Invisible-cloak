"""OCR stage: turn an image into positioned tokens using Tesseract.

This is the missing front of the pipeline. When the API receives an image but
no explicit OCR tokens, :func:`extract_tokens` runs Tesseract via
``pytesseract.image_to_data`` and returns :class:`~app.pipeline.locate.Token`
objects (text + pixel bbox), each carrying an OCR confidence. Those tokens flow
straight into the existing LOCATE stage, so token merging / reconstruction of
split numbers (e.g. ``7730`` ``0889`` ``2163`` -> ``7730 0889 2163``) and the
IoU bbox union are reused unchanged.

Tesseract is a *system* dependency (the ``tesseract`` binary + language data).
If it is not installed, OCR degrades gracefully to an empty token list and the
pipeline behaves exactly as before (no image OCR), rather than crashing.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from PIL import Image

from .locate import Box, Token

try:  # pytesseract is a hard dependency, but import defensively.
    import pytesseract
    from pytesseract import Output

    _PYTESSERACT_IMPORT_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - only when dep missing
    pytesseract = None  # type: ignore[assignment]
    Output = None  # type: ignore[assignment]
    _PYTESSERACT_IMPORT_ERROR = exc


# Allow overriding the binary / tessdata via env (useful on non-standard
# installs, e.g. a conda-forge tesseract).
_TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if _TESSERACT_CMD and pytesseract is not None:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

# Minimum per-token OCR confidence (0..100) to keep a token. Tesseract reports
# -1 for non-text blocks; those are always dropped.
_MIN_TOKEN_CONF = float(os.getenv("CLOAK_OCR_MIN_CONF", "30"))


@lru_cache(maxsize=1)
def tesseract_available() -> bool:
    """Return True if a usable Tesseract binary is reachable."""
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_unavailable_reason() -> Optional[str]:
    """Human-readable reason OCR is unavailable, or None if it works."""
    if pytesseract is None:
        return f"pytesseract import failed: {_PYTESSERACT_IMPORT_ERROR!r}"
    if not tesseract_available():
        return "tesseract binary not found on PATH (install system Tesseract)"
    return None


def extract_tokens(image: Image.Image, min_conf: float | None = None) -> list[Token]:
    """Run Tesseract over ``image`` and return positioned, confident tokens.

    Uses ``image_to_data`` so each token has text, an [x, y, w, h] pixel bbox
    and a confidence. Returns an empty list if Tesseract is unavailable.
    """
    if not tesseract_available():
        return []

    threshold = _MIN_TOKEN_CONF if min_conf is None else min_conf
    rgb = image.convert("RGB")
    data = pytesseract.image_to_data(rgb, output_type=Output.DICT)

    tokens: list[Token] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < threshold:
            continue
        x = float(data["left"][i])
        y = float(data["top"][i])
        w = float(data["width"][i])
        h = float(data["height"][i])
        if w <= 0 or h <= 0:
            continue
        tokens.append(Token(text=text, box=Box(x, y, w, h), confidence=conf))
    return tokens


def ocr_crop_text(crop: Image.Image) -> str:
    """OCR an already-cropped region image and return recognized text.

    Used by the VERIFY re-OCR loop (``verify_region`` crops the region, then
    passes the crop here). PSM 6 (assume a uniform block) reads short numeric
    fields more reliably than full-page segmentation on a tiny crop.
    """
    if not tesseract_available():
        return ""
    try:
        return pytesseract.image_to_string(crop.convert("RGB"), config="--psm 6").strip()
    except Exception:
        return ""


def ocr_text_in_region(image: Image.Image, box: Box) -> str:
    """OCR just the pixels inside ``box`` (convenience wrapper)."""
    if not tesseract_available():
        return ""
    x1 = max(0, int(box.x))
    y1 = max(0, int(box.y))
    x2 = min(image.width, int(box.x + box.w))
    y2 = min(image.height, int(box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return ""
    return ocr_crop_text(image.crop((x1, y1, x2, y2)))
