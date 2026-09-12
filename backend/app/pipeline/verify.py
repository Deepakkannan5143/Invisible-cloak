"""VERIFY stage: confirm sensitive content is no longer recoverable.

Ideal implementation: after baking the mask, re-run OCR on the protected image
crop and re-run detection; if the value is still readable, escalate protection
strength and retry (up to N attempts).

This environment has no OCR engine bundled, so verification is pluggable via an
``ocr_fn`` callback. When no OCR function is supplied we fall back to a
*structural* check: an obfuscated region is considered verified when a mask has
actually been applied to its pixels (measured as a large drop in local detail /
variance versus the original crop). This is honest about its limits — it proves
the pixels were altered, not that a state-of-the-art OCR could never recover
them. Wire a real ``ocr_fn`` (e.g. Tesseract/PaddleOCR) for a true re-OCR pass.
"""

from __future__ import annotations

from typing import Callable, Optional

from PIL import Image

from .detectors import detect_text
from .locate import Box, LocatedDetection

# ocr_fn(image_crop) -> recognized text
OcrFn = Callable[[Image.Image], str]

MAX_ATTEMPTS = 3


def _crop(img: Image.Image, box: Box) -> Image.Image:
    x1, y1 = max(0, int(box.x)), max(0, int(box.y))
    x2 = min(img.width, int(box.x + box.w))
    y2 = min(img.height, int(box.y + box.h))
    if x2 <= x1 or y2 <= y1:
        return Image.new("RGB", (1, 1))
    return img.crop((x1, y1, x2, y2))


def _detail_score(crop: Image.Image) -> float:
    """A cheap proxy for 'how much legible structure remains'.

    Mean absolute difference between the grayscale crop and its 1px-blurred
    self. Sharp text has high edge energy; heavy blur/pixelation/solid fill
    collapses it toward zero.
    """
    from PIL import ImageFilter

    g = crop.convert("L")
    b = g.filter(ImageFilter.GaussianBlur(radius=1))
    gp = list(g.getdata())
    bp = list(b.getdata())
    if not gp:
        return 0.0
    return sum(abs(a - c) for a, c in zip(gp, bp)) / len(gp)


def verify_region(
    protected_img: Image.Image,
    det: LocatedDetection,
    original_detail: float,
    ocr_fn: Optional[OcrFn] = None,
) -> bool:
    """Return True if the region is considered adequately protected."""
    crop = _crop(protected_img, det.box)

    if ocr_fn is not None:
        recovered = ocr_fn(crop)
        # If detection finds nothing sensitive of this type in the re-OCR'd
        # text, the region passes verification.
        remaining = detect_text(recovered, {det.type})
        return len(remaining) == 0

    # Structural fallback: detail must have dropped substantially.
    after = _detail_score(crop)
    if original_detail <= 1e-6:
        return True
    return after <= max(1.5, original_detail * 0.35)


def original_detail_for(img: Image.Image, det: LocatedDetection) -> float:
    return _detail_score(_crop(img, det.box))
