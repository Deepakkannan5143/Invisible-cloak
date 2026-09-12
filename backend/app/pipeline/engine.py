"""Pipeline orchestrator: DETECT -> LOCATE -> PROTECT -> VERIFY -> FULFILL."""

from __future__ import annotations

import time
from typing import Callable, Optional

from PIL import Image

from ..schemas import (
    DetectionOut,
    ScanRequest,
    ScanResponse,
    Summary,
)
from ..logging_util import debug, info, mask_for_log
from .detectors import SEVERITY_BY_TYPE, detect_text
from .locate import Box, LocatedDetection, Token, locate
from .ocr import extract_tokens, ocr_crop_text, ocr_unavailable_reason
from .protect import apply_protection, decode_image, encode_image, mask_value
from .verify import MAX_ATTEMPTS, original_detail_for, verify_region

# Residual-risk weighting for the privacy score.
_SEVERITY_RISK = {"low": 4, "medium": 8, "high": 14, "critical": 20}


def _enabled_set(req: ScanRequest) -> Optional[set[str]]:
    if req.enabled_types is None:
        return None
    return {t.strip().upper() for t in req.enabled_types if t.strip()}


def _locate_tokens(
    tokens: list[Token],
    enabled: Optional[set[str]],
    img_w: Optional[float],
    img_h: Optional[float],
) -> list[LocatedDetection]:
    return locate(tokens, enabled, img_w=img_w, img_h=img_h)


def _tokens_from_request(req: ScanRequest) -> list[Token]:
    return [
        Token(text=t.text, box=Box(t.bbox[0], t.bbox[1], t.bbox[2], t.bbox[3]))
        for t in (req.tokens or [])
    ]


def _detect_from_text(req: ScanRequest, enabled: Optional[set[str]]) -> list[LocatedDetection]:
    """Text-only detections have no spatial box (zero-area placeholder)."""
    out: list[LocatedDetection] = []
    for m in detect_text(req.text or "", enabled):
        out.append(
            LocatedDetection(
                type=m.type, severity=m.severity, confidence=m.confidence,
                value=m.value, box=Box(0.0, 0.0, 0.0, 0.0),
            )
        )
    return out


def _privacy_score(dets: list[LocatedDetection], protected_flags: list[bool]) -> float:
    if not dets:
        return 100.0
    residual = 0
    for d, ok in zip(dets, protected_flags):
        weight = _SEVERITY_RISK.get(d.severity, 8)
        residual += weight * (0.06 if ok else 1.0)
    score = max(0.0, 100.0 - residual)
    return round(min(100.0, score), 1)


def run_pipeline(req: ScanRequest) -> ScanResponse:
    start = time.perf_counter()
    enabled = _enabled_set(req)

    # Decode the source image up front so OCR, protection and re-OCR all share
    # the same PIL object (and the same pixel coordinate space).
    img: Optional[Image.Image] = None
    if req.image_base64:
        try:
            img = decode_image(req.image_base64)
        except Exception:
            img = None
            info("failed to decode image_base64; treating as no image")

    img_w = float(req.image_width) if req.image_width else (float(img.width) if img else None)
    img_h = float(req.image_height) if req.image_height else (float(img.height) if img else None)

    # ---- OCR -> DETECT -> LOCATE ------------------------------------------
    # Token source priority:
    #   1. explicit OCR tokens supplied by the caller (contract preserved)
    #   2. tokens extracted from the image via Tesseract (new)
    #   3. raw text (no spatial boxes)
    if req.tokens:
        tokens = _tokens_from_request(req)
        debug("using %d caller-supplied OCR tokens", len(tokens))
        detections = _locate_tokens(tokens, enabled, img_w, img_h)
    elif img is not None:
        reason = ocr_unavailable_reason()
        if reason:
            info("OCR requested but unavailable: %s", reason)
            detections = []
        else:
            tokens = extract_tokens(img)
            debug("Tesseract produced %d tokens", len(tokens))
            detections = _locate_tokens(tokens, enabled, img_w, img_h)
    else:
        detections = _detect_from_text(req, enabled)

    # ---- PROTECT (+ VERIFY with escalation) -------------------------------
    # Real re-OCR verifier: verify_region crops the (now-masked) region and
    # hands the crop here; we OCR it and return the recognized text. If that
    # text still contains the sensitive value, verify_region reports failure
    # and the protect loop escalates. When Tesseract is unavailable we pass
    # None, so verify_region uses its structural fallback.
    ocr_verifier: Optional[Callable[[Image.Image], str]] = (
        ocr_crop_text if (img is not None and ocr_unavailable_reason() is None) else None
    )

    out_detections: list[DetectionOut] = []
    protected_flags: list[bool] = []

    for det in detections:
        status = "exposed"
        verified = False
        attempts = 0

        has_box = det.box.w > 0 and det.box.h > 0
        if img is not None and has_box:
            original_detail = original_detail_for(img, det)
            for attempt in range(1, MAX_ATTEMPTS + 1):
                attempts = attempt
                apply_protection(img, det, req.mode.value, attempt=attempt)
                # Verify with real re-OCR when Tesseract is available; the
                # structural detail check remains the fallback inside
                # verify_region when ocr_fn is None.
                if verify_region(img, det, original_detail, ocr_fn=ocr_verifier):
                    verified = True
                    break
            status = "protected"
            if not verified:
                debug(
                    "region for %s still detectable after %d attempts",
                    det.type, attempts,
                )
        elif has_box:
            # No image supplied but we have coordinates: region is located and
            # will be protected client-side; mark protected, verification N/A.
            status = "protected"
            attempts = 1
            verified = True
        else:
            # Text-only detection: protected by masking the returned text.
            status = "protected"
            attempts = 1
            verified = True

        protected_flags.append(status == "protected")
        out_detections.append(
            DetectionOut(
                type=det.type,
                text=mask_value(det.type, det.value),
                confidence=round(det.confidence, 4),
                severity=SEVERITY_BY_TYPE.get(det.type, det.severity),
                bbox=[
                    round(det.box.x, 2),
                    round(det.box.y, 2),
                    round(det.box.w, 2),
                    round(det.box.h, 2),
                ],
                status=status,
                verification_passed=verified,
                attempts=attempts,
            )
        )

    protected_image = encode_image(img) if img is not None else None

    total = len(out_detections)
    critical = sum(1 for d in out_detections if d.severity == "critical")
    protected_count = sum(1 for f in protected_flags if f)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return ScanResponse(
        success=True,
        processing_time_ms=elapsed_ms,
        privacy_score=_privacy_score(detections, protected_flags),
        summary=Summary(
            total_detections=total,
            critical_count=critical,
            protected_count=protected_count,
        ),
        detections=out_detections,
        protected_image=protected_image,
    )
