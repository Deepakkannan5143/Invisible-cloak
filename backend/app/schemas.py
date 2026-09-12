"""Pydantic request/response schemas.

The response schema is the strict API contract consumed by clients. The request
schema accepts either raw text and/or a list of OCR tokens with pixel bounding
boxes (as would be produced by an OCR / vision service upstream).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProtectionMode(str, Enum):
    BLUR = "blur"
    PIXELATE = "pixelate"
    REDACT = "redact"
    FROSTED = "frosted"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class OcrToken(BaseModel):
    """A single OCR token with its pixel-space bounding box.

    bbox is [x, y, width, height] in pixels relative to the source image.
    """

    text: str
    # [x, y, width, height] in pixels
    bbox: list[float] = Field(..., min_length=4, max_length=4)


class CustomPattern(BaseModel):
    """A user-provided custom detection pattern (Protection Settings §12).

    ``regex`` is optional — when omitted, ``name`` is matched as a literal
    (case-insensitive) phrase. Patterns are validated/compiled defensively on
    the backend (length-capped, ReDoS shapes rejected); a bad pattern is
    skipped rather than failing the whole scan.
    """

    name: str
    regex: Optional[str] = None
    confidence: Optional[float] = None
    description: Optional[str] = None


class ScanRequest(BaseModel):
    """Incoming payload.

    Provide any of:
      - ``text``: free text to scan (no spatial redaction possible).
      - ``tokens``: OCR tokens with pixel bboxes (enables spatial redaction).
      - ``image_base64``: a data URL or bare base64 PNG/JPEG to redact.
    """

    text: Optional[str] = None
    tokens: Optional[list[OcrToken]] = None
    image_base64: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    mode: ProtectionMode = ProtectionMode.FROSTED
    # If provided, only these types are protected. Accepts canonical
    # SensitiveType names (e.g. "AADHAAR", "CREDIT_CARD") or frontend toggle
    # labels / aliases (e.g. "credit_card", "phone", "custom"), which the
    # backend normalizes. None => all types.
    enabled_types: Optional[list[str]] = None
    # User-defined custom detection patterns. Only run when the CUSTOM_PATTERN
    # (frontend "Custom Pattern") type is enabled.
    custom_patterns: Optional[list[CustomPattern]] = None


# ---------------------------------------------------------------------------
# Response (strict contract)
# ---------------------------------------------------------------------------

class DetectionOut(BaseModel):
    type: str
    text: str  # always a masked / redacted placeholder — never the raw value
    confidence: float  # 0..1
    severity: str  # low | medium | high | critical
    bbox: list[float]  # [x, y, width, height] in pixels
    status: str  # "protected" | "exposed"
    verification_passed: bool
    attempts: int


class Summary(BaseModel):
    total_detections: int
    critical_count: int
    protected_count: int


class ScanResponse(BaseModel):
    success: bool
    processing_time_ms: float
    privacy_score: float
    summary: Summary
    detections: list[DetectionOut]
    protected_image: Optional[str] = None  # data:image/png;base64,...
