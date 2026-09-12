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
import re
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


# Upscale factor for the secondary OCR pass. Small text and high-entropy
# credentials (API keys, tokens) are read more reliably when enlarged. Env
# override so the pass can be tuned/disabled per deployment.
_UPSCALE = float(os.getenv("CLOAK_OCR_UPSCALE", "2.0"))
# Enable/disable the extra preprocessing pass (on by default; §3). Set to
# "false" to run a single pass for maximum speed.
_PREPROCESS = os.getenv("CLOAK_OCR_PREPROCESS", "true").strip().lower() in (
    "1", "true", "yes", "on"
)

# High-entropy credential tokens (API keys, access tokens, AWS keys) are hard
# for Tesseract to read confidently because they are not words — it often
# assigns them a very low confidence even when the characters are essentially
# correct. When a token carries an unmistakable credential prefix we keep it
# regardless of OCR confidence, because the prefix itself is strong intrinsic
# evidence (the downstream detector still validates structure/context). This is
# deterministic and leaks nothing.
_CREDENTIAL_TOKEN_RE = re.compile(
    r"^(?:sk-|pk-|rk_|xox[baprs]-|ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|"
    r"AKIA|ASIA|eyJ)[A-Za-z0-9._\-\]/+]{6,}"
)


def _tokens_from_data(data: dict, threshold: float, scale: float = 1.0,
                      rescue_credentials: bool = False) -> list[Token]:
    """Convert a Tesseract ``image_to_data`` dict into Tokens, rescaling boxes.

    ``scale`` is the factor the source image was enlarged by before OCR; boxes
    are divided back to the original coordinate space so every pass shares one
    pixel grid (§3: preserve bounding boxes when combining variants).

    ``rescue_credentials`` keeps tokens whose text carries a strong credential
    prefix (sk-, ghp_, AKIA, ...) even below the confidence threshold, because
    the prefix is strong intrinsic evidence that OCR confidence understates.
    """
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
        is_credential = rescue_credentials and bool(_CREDENTIAL_TOKEN_RE.match(text))
        if conf < threshold and not is_credential:
            continue
        x = float(data["left"][i]) / scale
        y = float(data["top"][i]) / scale
        w = float(data["width"][i]) / scale
        h = float(data["height"][i]) / scale
        if w <= 0 or h <= 0:
            continue
        tokens.append(Token(text=text, box=Box(x, y, w, h), confidence=conf))
    return tokens


def _box_iou(a: Box, b: Box) -> float:
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(a.x + a.w, b.x + b.w), min(a.y + a.h, b.y + b.h)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def _overlap_area(a: Box, b: Box) -> float:
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(a.x + a.w, b.x + b.w), min(a.y + a.h, b.y + b.h)
    return max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)


def _merge_token_sets(primary: list[Token], extra: list[Token]) -> list[Token]:
    """Add tokens from a secondary pass that the primary pass genuinely missed.

    A secondary token is dropped when it overlaps existing primary tokens at
    all substantially — measured as the fraction of the secondary token's OWN
    area that is already covered by primary tokens. This prevents a wider
    OCR-merged token (e.g. an 8/12-digit run spanning several 4-digit groups)
    from being *added alongside* the individual groups and corrupting the line
    reconstruction. The primary pass stays authoritative (§3); only truly new
    regions (e.g. a recovered API key) are added.
    """
    merged = list(primary)
    for t in extra:
        area = max(1e-6, t.box.w * t.box.h)
        covered = sum(_overlap_area(t.box, p.box) for p in primary)
        if covered / area > 0.25:
            continue  # this region is already represented by primary tokens
        merged.append(t)
    return merged


def extract_tokens(image: Image.Image, min_conf: float | None = None) -> list[Token]:
    """Run Tesseract over ``image`` and return positioned, confident tokens.

    Uses ``image_to_data`` so each token has text, an [x, y, w, h] pixel bbox
    and a confidence. A second, upscaled pass (§3 preprocessing) is run only
    when it can help — enlarging the image recovers small / high-entropy tokens
    (API keys, tokens) that the base pass reads with low confidence or misses
    entirely. Extra tokens are merged back into the base coordinate space and
    de-duplicated by bbox overlap. Returns an empty list if Tesseract is
    unavailable.
    """
    if not tesseract_available():
        return []

    threshold = _MIN_TOKEN_CONF if min_conf is None else min_conf
    rgb = image.convert("RGB")
    base = _tokens_from_data(
        pytesseract.image_to_data(rgb, output_type=Output.DICT), threshold
    )

    if not _PREPROCESS or _UPSCALE <= 1.0:
        return base

    # Secondary preprocessing pass: upscale + grayscale so faint / dense text
    # is enlarged for the engine. Run at a slightly lower confidence floor so a
    # token the base pass dropped can still be recovered, then merged in.
    try:
        w2 = max(1, int(rgb.width * _UPSCALE))
        h2 = max(1, int(rgb.height * _UPSCALE))
        up = rgb.resize((w2, h2), Image.LANCZOS).convert("L").convert("RGB")
        extra_threshold = max(0.0, threshold - 10.0)
        extra = _tokens_from_data(
            pytesseract.image_to_data(up, output_type=Output.DICT),
            extra_threshold, scale=_UPSCALE, rescue_credentials=True,
        )
        return _merge_token_sets(base, extra)
    except Exception:  # pragma: no cover - preprocessing is best-effort
        return base


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
