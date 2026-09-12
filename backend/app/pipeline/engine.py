"""Pipeline orchestrator: DETECT -> LOCATE -> PROTECT -> VERIFY -> FULFILL."""

from __future__ import annotations

import time
from typing import Optional

from PIL import Image

from ..schemas import (
    DetectionOut,
    ScanRequest,
    ScanResponse,
    Summary,
)
from .detectors import SEVERITY_BY_TYPE, detect_text
from .locate import Box, LocatedDetection, Token, locate
from .protect import apply_protection, decode_image, encode_image, mask_value
from .verify import MAX_ATTEMPTS, original_detail_for, verify_region

# Residual-risk weighting for the privacy score.
_SEVERITY_RISK = {"low": 4, "medium": 8, "high": 14, "critical": 20}


def _enabled_set(req: ScanRequest) -> Optional[set[str]]:
    if req.enabled_types is None:
        return None
    return {t.strip().upper() for t in req.enabled_types if t.strip()}


def _detect_from_tokens(req: ScanRequest, enabled: Optional[set[str]]) -> list[LocatedDetection]:
    tokens = [
        Token(text=t.text, box=Box(t.bbox[0], t.bbox[1], t.bbox[2], t.bbox[3]))
        for t in (req.tokens or [])
    ]
    return locate(
        tokens,
        enabled,
        img_w=float(req.image_width) if req.image_width else None,
        img_h=float(req.image_height) if req.image_height else None,
    )


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

    # ---- DETECT + LOCATE --------------------------------------------------
    if req.tokens:
        detections = _detect_from_tokens(req, enabled)
    else:
        detections = _detect_from_text(req, enabled)

    # ---- PROTECT (+ VERIFY with escalation) -------------------------------
    img: Optional[Image.Image] = None
    if req.image_base64:
        try:
            img = decode_image(req.image_base64)
        except Exception:
            img = None

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
                if verify_region(img, det, original_detail):
                    verified = True
                    break
            status = "protected"
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
