"""DETECT stage: pattern definitions + the raw-text detector.

Each :class:`PatternDef` pairs a regex with a severity, optional checksum
validator, and context keywords. Detection over free text is the foundation;
the LOCATE stage reuses these same patterns over merged OCR token lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .validators import is_valid_ipv4, luhn_check, verhoeff_check


@dataclass(frozen=True)
class Match:
    type: str
    severity: str
    start: int
    end: int
    value: str
    confidence: float


@dataclass(frozen=True)
class PatternDef:
    type: str
    severity: str
    regex: re.Pattern
    base_confidence: float
    # Optional checksum/structural validator on the matched value.
    validator: Optional[Callable[[str], bool]] = None
    # If a validator exists and fails, drop the match entirely when
    # ``require_valid`` is True; otherwise just lower confidence.
    require_valid: bool = False
    context_keywords: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Pattern library. Ordered so that more specific / higher-severity patterns are
# preferred when spans overlap (resolved in ``detect_text``).
# ---------------------------------------------------------------------------

_P = re.compile

PATTERNS: list[PatternDef] = [
    # ---- C. System / Security credentials (most specific first) -----------
    PatternDef(
        "PRIVATE_KEY", "critical",
        _P(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        0.99,
    ),
    PatternDef(
        "AWS_ACCESS_KEY", "critical",
        _P(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        0.98,
    ),
    PatternDef(
        "API_KEY", "critical",
        _P(r"\bsk-(?:live-|test-|proj-)?[A-Za-z0-9]{16,64}\b"),
        0.97, context_keywords=("api", "key", "secret", "openai"),
    ),
    PatternDef(
        "ACCESS_TOKEN", "high",
        _P(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        0.97, context_keywords=("token", "github", "access"),
    ),
    PatternDef(
        "JWT_TOKEN", "high",
        _P(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        0.96,
    ),
    PatternDef(
        "PASSWORD", "high",
        _P(r"(?i)\b(?:password|passwd|pwd|secret)\s*[:=]\s*(\S{4,})"),
        0.9, context_keywords=("password", "secret", "login"),
    ),
    # ---- B. Financial ------------------------------------------------------
    PatternDef(
        "CREDIT_CARD", "critical",
        _P(r"\b(?:\d[ -]?){12,18}\d\b"),
        0.9, validator=luhn_check, require_valid=True,
        context_keywords=("card", "credit", "debit", "visa", "mastercard", "cvv"),
    ),
    PatternDef(
        "IBAN", "high",
        _P(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
        0.9, context_keywords=("iban", "bank", "account"),
    ),
    PatternDef(
        "SWIFT_BIC", "high",
        _P(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
        0.7, context_keywords=("swift", "bic", "bank"),
    ),
    PatternDef(
        "IFSC", "high",
        _P(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        0.9, context_keywords=("ifsc", "bank", "branch"),
    ),
    PatternDef(
        "UPI_ID", "high",
        _P(r"\b[A-Za-z0-9.\-_]{2,}@(?:okhdfcbank|oksbi|okaxis|okicici|paytm|ybl|upi|apl|axl)\b"),
        0.95, context_keywords=("upi", "vpa", "pay"),
    ),
    PatternDef(
        "CRYPTO_WALLET", "high",
        _P(r"\b(?:0x[a-fA-F0-9]{40}|bc1[a-z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
        0.85, context_keywords=("wallet", "btc", "eth", "bitcoin", "ethereum"),
    ),
    # ---- A. Government / national IDs -------------------------------------
    PatternDef(
        "AADHAAR", "critical",
        _P(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
        0.85, validator=verhoeff_check, require_valid=False,
        context_keywords=("aadhaar", "uidai", "aadhar", "uid"),
    ),
    PatternDef(
        "PAN", "critical",
        _P(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
        0.92, context_keywords=("pan", "permanent account"),
    ),
    PatternDef(
        "SSN", "critical",
        _P(r"\b\d{3}-\d{2}-\d{4}\b"),
        0.9, context_keywords=("ssn", "social security"),
    ),
    PatternDef(
        "PASSPORT", "critical",
        _P(r"\b[A-Z][0-9]{7}\b"),
        0.72, context_keywords=("passport"),
    ),
    PatternDef(
        "UK_NINO", "critical",
        _P(r"\b[ABCEGHJ-PRSTW][ABCEGHJ-NPRSTW]\d{6}[A-D]\b"),
        0.88, context_keywords=("national insurance", "nino"),
    ),
    PatternDef(
        "KR_RRN", "critical",
        _P(r"\b\d{6}-[1-4]\d{6}\b"),
        0.9, context_keywords=("resident registration", "rrn"),
    ),
    # ---- D. Contact / demographic PII -------------------------------------
    PatternDef(
        "EMAIL", "medium",
        _P(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        0.98, context_keywords=("email", "mail", "contact"),
    ),
    PatternDef(
        # Matches E.164-ish and common national groupings: an optional +CC,
        # then 10-11 digits split by spaces/hyphens into 2-4 groups.
        "PHONE", "medium",
        _P(r"(?<![\w.])\+?\d{1,3}[ -]?(?:\d[ -]?){8,11}\d(?![\w.])"),
        0.7, context_keywords=("phone", "mobile", "tel", "call", "contact"),
    ),
    PatternDef(
        "IP_ADDRESS", "low",
        _P(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        0.9, validator=is_valid_ipv4, require_valid=True,
        context_keywords=("ip", "address", "host", "server"),
    ),
    PatternDef(
        "MAC_ADDRESS", "low",
        _P(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
        0.9, context_keywords=("mac", "hardware"),
    ),
]

# Fast lookup for severity by type (also used by LOCATE / VERIFY).
SEVERITY_BY_TYPE: dict[str, str] = {p.type: p.severity for p in PATTERNS}

CONTEXT_WINDOW = 40  # chars on each side to scan for context keywords


def _has_context(text: str, start: int, end: int, keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return False
    lo = max(0, start - CONTEXT_WINDOW)
    hi = min(len(text), end + CONTEXT_WINDOW)
    window = text[lo:hi].lower()
    return any(k in window for k in keywords)


def _score(pattern: PatternDef, text: str, start: int, end: int, value: str) -> Optional[float]:
    """Compute final confidence for a raw match, or None to reject it."""
    conf = pattern.base_confidence
    has_ctx = _has_context(text, start, end, pattern.context_keywords)

    if pattern.validator is not None:
        ok = pattern.validator(value)
        if ok:
            conf = min(0.99, conf + 0.08)
        elif pattern.require_valid:
            return None
        else:
            # Failed a non-mandatory checksum: penalize, but less so when strong
            # context is present (OCR noise shouldn't discard a labelled field).
            conf = max(0.3, conf - (0.18 if has_ctx else 0.35))

    # Context scoring: nearby keywords meaningfully raise confidence so a
    # context-anchored type wins overlaps against generic numeric patterns.
    if has_ctx:
        conf = min(0.99, conf + 0.15)
    return round(conf, 4)


def detect_text(text: str, enabled_types: Optional[set[str]] = None) -> list[Match]:
    """Run all patterns over ``text`` and return non-overlapping matches.

    Overlaps are resolved by preferring higher confidence, then longer spans.
    """
    raw: list[Match] = []
    for pattern in PATTERNS:
        if enabled_types is not None and pattern.type not in enabled_types:
            continue
        for m in pattern.regex.finditer(text):
            # Prefer a capture group when the pattern defines one (e.g. PASSWORD).
            if m.groups():
                value = m.group(1)
                start, end = m.start(1), m.end(1)
            else:
                value = m.group(0)
                start, end = m.start(0), m.end(0)
            conf = _score(pattern, text, start, end, value)
            if conf is None:
                continue
            raw.append(Match(pattern.type, pattern.severity, start, end, value, conf))

    return _resolve_overlaps(raw)


def _resolve_overlaps(matches: list[Match]) -> list[Match]:
    # Sort by confidence desc, then span length desc — greedily keep winners.
    ordered = sorted(
        matches, key=lambda m: (m.confidence, m.end - m.start), reverse=True
    )
    kept: list[Match] = []
    for m in ordered:
        if any(not (m.end <= k.start or m.start >= k.end) for k in kept):
            continue  # overlaps an already-kept (higher priority) match
        kept.append(m)
    kept.sort(key=lambda m: m.start)
    return kept
