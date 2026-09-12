"""DETECT stage: pattern definitions + the raw-text detector.

Each :class:`PatternDef` pairs a regex with a severity, optional checksum
validator, and context keywords. Detection over free text is the foundation;
the LOCATE stage reuses these same patterns over merged OCR token lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .context import score_candidate
from .validators import is_valid_ipv4, luhn_check, verhoeff_check


@dataclass(frozen=True)
class Match:
    type: str
    severity: str
    start: int
    end: int
    value: str
    confidence: float
    # Human-readable evidence for *why* this was flagged (never the raw value).
    signals: tuple[str, ...] = ()


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
    # When True, the ``regex`` matches a *label* anchor (e.g. "CVV") and the
    # actual sensitive value is found by ``value_regex`` immediately after it.
    # The detection is dropped unless card/related context is present.
    require_context: bool = False
    value_regex: Optional[re.Pattern] = None


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
    # CVV / expiry are only meaningful near card context; ``require_context``
    # means they are dropped unless the context model finds card keywords, so
    # they never fire on a random 3-digit number or an arbitrary date.
    PatternDef(
        "CVV", "high",
        _P(r"(?i)\b(?:cvv|cvc|card verification(?:\s+value)?)\b"),  # label anchor
        0.5, context_keywords=("cvv", "cvc"), require_context=True,
        value_regex=_P(r"\d{3,4}"),
    ),
    PatternDef(
        "CARD_EXPIRY", "medium",
        _P(r"(?i)\b(?:valid\s+thru|valid\s+through|expiry|expiration|exp)\b"),
        0.5, context_keywords=("expiry", "expiration", "valid thru", "valid through"),
        require_context=True,
        value_regex=_P(r"(0[1-9]|1[0-2])\s*/\s*\d{2,4}"),
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

# Character window each side of a candidate scanned for context keywords. Used
# for the text path; the spatial (LOCATE) path augments this window with tokens
# from spatially-near lines before calling detect_text.
CONTEXT_WINDOW = 48

# Types that are just a bare numeric run with no distinctive structure — these
# get the weak-random penalty unless corroborated.
_BARE_NUMERIC_TYPES = frozenset({"AADHAAR", "CREDIT_CARD", "DEBIT_CARD", "PHONE"})


def _context_window(text: str, start: int, end: int) -> str:
    lo = max(0, start - CONTEXT_WINDOW)
    hi = min(len(text), end + CONTEXT_WINDOW)
    return text[lo:hi]


def _adjacent_keyword(text: str, start: int, end: int, keywords: tuple[str, ...]) -> bool:
    """True if a keyword sits in the tight window immediately around the value."""
    lo = max(0, start - 20)
    hi = min(len(text), end + 12)
    tight = " ".join(text[lo:hi].lower().split())
    return any(k in tight for k in keywords)


def _score(
    pattern: PatternDef, text: str, start: int, end: int, value: str
) -> Optional[tuple[float, tuple[str, ...]]]:
    """Return (confidence 0..1, signals) for a match, or None to reject it.

    Delegates the additive scoring to the context model while preserving the
    original guarantees: ``require_valid`` types are dropped on failed checksum.
    """
    validated: Optional[bool] = None
    if pattern.validator is not None:
        validated = bool(pattern.validator(value))
        if not validated and pattern.require_valid:
            return None  # e.g. a non-Luhn 16-digit run is never a card

    window = _context_window(text, start, end)
    kws = pattern.context_keywords
    adjacent = _adjacent_keyword(text, start, end, kws) if kws else False

    scored = score_candidate(
        pattern.type,
        pattern_matched=True,
        validated=validated,
        context_window=window,
        adjacent=adjacent,
        is_bare_numeric=pattern.type in _BARE_NUMERIC_TYPES,
    )

    # Blend the model score with the pattern's intrinsic base confidence.
    #
    # Highly-specific patterns (JWT, private key, email, PAN, ...) carry little
    # ambiguity, so they keep their strong prior via max(). But ambiguous
    # bare-numeric types (phone / card / Aadhaar) must be governed by the
    # context model — otherwise a contextless phone-shaped number would always
    # win on its base prior and out-rank a context-anchored Aadhaar on the same
    # span. For those, we trust the model score directly.
    if pattern.type in _BARE_NUMERIC_TYPES:
        conf = scored.confidence
    elif validated is False:
        conf = scored.confidence
    else:
        conf = max(scored.confidence, pattern.base_confidence)
    conf = round(min(0.99, conf), 4)
    return conf, tuple(scored.signals)


def detect_text(text: str, enabled_types: Optional[set[str]] = None) -> list[Match]:
    """Run all patterns over ``text`` and return non-overlapping matches.

    Overlaps are resolved by preferring higher confidence, then longer spans.
    """
    raw: list[Match] = []
    for pattern in PATTERNS:
        if enabled_types is not None and pattern.type not in enabled_types:
            continue

        if pattern.require_context and pattern.value_regex is not None:
            raw.extend(_detect_label_anchored(pattern, text))
            continue

        for m in pattern.regex.finditer(text):
            # Prefer a capture group when the pattern defines one (e.g. PASSWORD).
            if m.groups():
                value = m.group(1)
                start, end = m.start(1), m.end(1)
            else:
                value = m.group(0)
                start, end = m.start(0), m.end(0)
            result = _score(pattern, text, start, end, value)
            if result is None:
                continue
            conf, signals = result
            raw.append(
                Match(pattern.type, pattern.severity, start, end, value, conf, signals)
            )

    return _resolve_overlaps(raw)


def _detect_label_anchored(pattern: PatternDef, text: str) -> list[Match]:
    """Detect label-anchored values (CVV, expiry): the value must sit right
    after a card/related label, and card context must be present. This is what
    stops every 3-digit number or date from being flagged."""
    out: list[Match] = []
    assert pattern.value_regex is not None
    for label in pattern.regex.finditer(text):
        # Look for the value within a short span after the label.
        search_lo = label.end()
        search_hi = min(len(text), label.end() + 24)
        vm = pattern.value_regex.search(text, search_lo, search_hi)
        if not vm:
            continue
        value = vm.group(0)
        window = _context_window(text, label.start(), vm.end())
        scored = score_candidate(
            pattern.type,
            pattern_matched=True,
            validated=None,
            context_window=window,
            adjacent=True,  # value is by construction adjacent to its label
        )
        # Require real card context (strong or medium tier present).
        if not scored.signals or all("context" not in s for s in scored.signals):
            continue
        conf = round(min(0.99, max(scored.confidence, 0.6)), 4)
        out.append(
            Match(pattern.type, pattern.severity, vm.start(), vm.end(),
                  value, conf, tuple(scored.signals))
        )
    return out


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
