"""Context-aware confidence model.

This module is the shared "brain" for turning a raw pattern hit into a
confidence score, combining intrinsic evidence (pattern + checksum validation)
with contextual evidence (nearby keywords, spatial proximity) and negative
suppression. It is used by both the text path (``detectors.detect_text``) and
the spatial path (``locate.locate``), so the two stay consistent.

Design goals (all local, deterministic, privacy-preserving — no LLM/API):

* An additive point model, not a boolean keyword check.
* A centralized, easily-extensible keyword dictionary.
* Positive context tiers (strong / medium / weak) per sensitive type.
* Negative context that actively suppresses (Order/Invoice/Reference numbers).
* Human-readable *signals* explaining every decision — never the raw value.
* Configurable thresholds deciding redact vs. skip.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Point weights (§9 confidence model). Final score is clamped to 0..100 and
# then normalized to a 0..1 confidence for the rest of the pipeline.
# ---------------------------------------------------------------------------

W_PATTERN = 20          # a candidate matched the type's structural pattern
W_VALIDATION_STRONG = 40  # passed a strong checksum (Luhn / Verhoeff / IPv4)
W_CONTEXT_STRONG = 30
W_CONTEXT_MEDIUM = 15
W_CONTEXT_WEAK = 6
W_SPATIAL_PROXIMITY = 10   # a context keyword sits right next to the candidate
W_CORROBORATION = 10       # >1 independent contextual cue

P_NEGATIVE_CONTEXT = 30    # subtracted when a suppressing label is nearby
P_FAILED_VALIDATION = 30   # subtracted when a checksum-bearing type fails it
P_WEAK_RANDOM = 20         # subtracted for a bare numeric candidate, no support

# Redaction thresholds (0..100). Tunable per deployment.
HIGH_CONFIDENCE_THRESHOLD = 75.0
MEDIUM_CONFIDENCE_THRESHOLD = 45.0
# A candidate is only redacted when its score reaches this floor.
REDACT_THRESHOLD = MEDIUM_CONFIDENCE_THRESHOLD


# ---------------------------------------------------------------------------
# Centralized context keyword dictionary (§2). Extend freely.
#
# Each sensitive type maps to strong / medium / weak keyword tiers. Keywords
# are lowercase; multi-word phrases are matched as substrings of a normalized
# (lowercased, whitespace-collapsed) context window.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContextTiers:
    strong: tuple[str, ...] = ()
    medium: tuple[str, ...] = ()
    weak: tuple[str, ...] = ()


# Shared vocabularies so several card types can reference the same lists.
_CARD_STRONG = (
    "card number", "card no", "debit card", "credit card", "card holder",
    "cardholder", "valid thru", "valid through", "bank card", "payment card",
)
_CARD_MEDIUM = (
    "card", "debit", "credit", "visa", "mastercard", "master card", "rupay",
    "amex", "payment", "expiry", "expiration", "cvv", "cvc",
)

_IDENTITY_STRONG = (
    "aadhaar", "aadhar", "uidai", "aadhaar number", "aadhar number",
    "government id", "identity number", "id number",
)
_IDENTITY_MEDIUM = ("uid", "identity", "national id")

_BANK_STRONG = (
    "account number", "account no", "bank account", "beneficiary",
    "customer id", "customer number", "transaction id", "upi id",
)
_BANK_MEDIUM = (
    "account", "bank", "branch", "ifsc", "upi", "transaction", "vpa",
)

_CRED_STRONG = (
    "password", "passcode", "api key", "access key", "private key",
    "secret key", "authorization", "bearer", "credential",
)
_CRED_MEDIUM = ("pin", "otp", "secret", "token", "login", "auth")

_NET_STRONG = ("ip address", "mac address", "ipv4", "endpoint")
_NET_MEDIUM = ("server", "host", "network", "ip")

_WEAK_GENERIC = ("id", "number", "no", "code")

CONTEXT: dict[str, ContextTiers] = {
    "CREDIT_CARD": ContextTiers(_CARD_STRONG, _CARD_MEDIUM, _WEAK_GENERIC),
    "DEBIT_CARD": ContextTiers(_CARD_STRONG, _CARD_MEDIUM, _WEAK_GENERIC),
    "CVV": ContextTiers(("cvv", "cvc", "security code", "card verification"),
                        ("card", "credit", "debit"), ()),
    "CARD_EXPIRY": ContextTiers(("valid thru", "valid through", "expiry", "expiration"),
                                ("card", "credit", "debit"), ()),
    "AADHAAR": ContextTiers(_IDENTITY_STRONG, _IDENTITY_MEDIUM, _WEAK_GENERIC),
    "PAN": ContextTiers(("pan", "permanent account", "pan number"),
                        ("tax", "income tax"), _WEAK_GENERIC),
    "SSN": ContextTiers(("ssn", "social security"), ("social",), _WEAK_GENERIC),
    "PASSPORT": ContextTiers(("passport", "passport number"), ("travel",), _WEAK_GENERIC),
    "UK_NINO": ContextTiers(("national insurance", "nino"), (), _WEAK_GENERIC),
    "KR_RRN": ContextTiers(("resident registration", "rrn"), (), _WEAK_GENERIC),
    "IBAN": ContextTiers(("iban",) + _BANK_STRONG, _BANK_MEDIUM, _WEAK_GENERIC),
    "SWIFT_BIC": ContextTiers(("swift", "bic"), _BANK_MEDIUM, _WEAK_GENERIC),
    "IFSC": ContextTiers(("ifsc",), _BANK_MEDIUM, _WEAK_GENERIC),
    "UPI_ID": ContextTiers(("upi id", "vpa"), _BANK_MEDIUM, _WEAK_GENERIC),
    "BANK_ACCOUNT": ContextTiers(_BANK_STRONG, _BANK_MEDIUM, _WEAK_GENERIC),
    "CRYPTO_WALLET": ContextTiers(("wallet address", "wallet"),
                                  ("btc", "eth", "bitcoin", "ethereum", "crypto"), ()),
    "API_KEY": ContextTiers(_CRED_STRONG, _CRED_MEDIUM, _WEAK_GENERIC),
    "ACCESS_TOKEN": ContextTiers(_CRED_STRONG + ("github",), _CRED_MEDIUM, _WEAK_GENERIC),
    "JWT_TOKEN": ContextTiers(_CRED_STRONG, _CRED_MEDIUM, ()),
    "PRIVATE_KEY": ContextTiers(_CRED_STRONG, _CRED_MEDIUM, ()),
    "PASSWORD": ContextTiers(_CRED_STRONG, _CRED_MEDIUM, _WEAK_GENERIC),
    "EMAIL": ContextTiers(("email", "e-mail"), ("mail", "contact"), ()),
    "PHONE": ContextTiers(("phone number", "mobile number", "contact number"),
                          ("phone", "mobile", "tel", "call", "contact"), _WEAK_GENERIC),
    "IP_ADDRESS": ContextTiers(_NET_STRONG, _NET_MEDIUM, ()),
    "MAC_ADDRESS": ContextTiers(("mac address",), ("mac", "hardware", "network"), ()),
}

# ---------------------------------------------------------------------------
# Negative context (§8). If any of these labels sit near a *checksum-less* or
# generic numeric candidate, strongly suppress it. Sensitive types that carry
# their own strong validation (e.g. a Luhn-valid card, a Verhoeff-valid
# Aadhaar) are only mildly affected — real card data can appear on an invoice.
# ---------------------------------------------------------------------------

NEGATIVE_CONTEXT: tuple[str, ...] = (
    "order number", "order id", "order no", "invoice number", "invoice no",
    "invoice", "reference number", "reference no", "ref no", "product code",
    "product id", "sku", "serial number", "serial no", "tracking number",
    "tracking id", "ticket number", "case number", "receipt", "postal code",
    "zip code", "pincode", "pin code", "otp", "quantity", "price", "amount",
    "date", "timestamp", "version", "port",
)

# Types whose intrinsic validation is strong enough that negative labels should
# only mildly reduce (not veto) the score.
STRONG_VALIDATION_TYPES: frozenset[str] = frozenset(
    {"CREDIT_CARD", "DEBIT_CARD", "AADHAAR", "IP_ADDRESS"}
)


@dataclass
class Scored:
    """Result of scoring a candidate — confidence plus the *why*."""
    confidence: float  # normalized 0..1
    score: float       # raw 0..100
    signals: list[str] = field(default_factory=list)
    suppressed: bool = False  # negative context dominated


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def find_keywords(window: str, keywords: tuple[str, ...]) -> list[str]:
    norm = _normalize(window)
    return [k for k in keywords if k in norm]


def negative_hits(window: str) -> list[str]:
    return find_keywords(window, NEGATIVE_CONTEXT)


def score_candidate(
    dtype: str,
    *,
    pattern_matched: bool,
    validated: bool | None,
    context_window: str,
    adjacent: bool,
    is_bare_numeric: bool = False,
) -> Scored:
    """Combine intrinsic + contextual evidence into a 0..100 score.

    Parameters
    ----------
    dtype: the sensitive type key (matches :data:`CONTEXT`).
    pattern_matched: whether the structural pattern matched (usually True).
    validated: True/False if a checksum ran, None if the type has no checksum.
    context_window: nearby text (same line + spatially-near lines) to inspect.
    adjacent: True when a strong/medium keyword sits immediately beside the
        candidate (spatial proximity bonus, §4).
    is_bare_numeric: True for a generic numeric candidate with no distinctive
        structure of its own (used to apply the weak-random penalty).
    """
    signals: list[str] = []
    score = 0.0

    if pattern_matched:
        score += W_PATTERN
        signals.append(f"{dtype.lower()} pattern matched")

    # Positive context tiers (computed first so validation penalty can be
    # softened when a strong label corroborates the field — OCR may misread a
    # single digit, but "Aadhaar Number:" still means the field is an Aadhaar).
    tiers = CONTEXT.get(dtype, ContextTiers())
    strong = find_keywords(context_window, tiers.strong)
    medium = find_keywords(context_window, tiers.medium)
    weak = find_keywords(context_window, tiers.weak)

    # Intrinsic validation.
    if validated is True:
        score += W_VALIDATION_STRONG
        signals.append("strong validation passed")
    elif validated is False:
        penalty = P_FAILED_VALIDATION
        if strong:
            penalty = 12  # strong label present: treat as OCR noise, not a veto
        score -= penalty
        signals.append("validation failed")

    cue_count = 0
    if strong:
        score += W_CONTEXT_STRONG
        cue_count += 1
        signals.append(f"strong context: {strong[0]}")
    if medium:
        score += W_CONTEXT_MEDIUM
        cue_count += 1
        signals.append(f"medium context: {medium[0]}")
    if weak and not strong and not medium:
        score += W_CONTEXT_WEAK
        signals.append(f"weak context: {weak[0]}")

    if adjacent and (strong or medium):
        score += W_SPATIAL_PROXIMITY
        signals.append("spatial proximity to keyword")

    if cue_count >= 2:
        score += W_CORROBORATION
        signals.append("multiple corroborating cues")

    # Negative context / suppression.
    negatives = negative_hits(context_window)
    suppressed = False
    if negatives:
        if dtype in STRONG_VALIDATION_TYPES and validated is True:
            # Real validated data can appear on an invoice; only mild nudge.
            score -= 10
            signals.append(f"negative context (mild, validated): {negatives[0]}")
        else:
            score -= P_NEGATIVE_CONTEXT
            signals.append(f"negative context: {negatives[0]}")
            suppressed = True

    # Weak/random numeric with nothing supporting it.
    if is_bare_numeric and not strong and not medium and validated is not True:
        score -= P_WEAK_RANDOM
        signals.append("bare numeric without corroboration")

    score = max(0.0, min(100.0, score))
    return Scored(confidence=round(score / 100.0, 4), score=round(score, 1),
                  signals=signals, suppressed=suppressed)
