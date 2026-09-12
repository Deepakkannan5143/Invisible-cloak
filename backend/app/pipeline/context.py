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
    "ADDRESS": ContextTiers(
        ("address", "home address", "residential address", "permanent address",
         "office address", "billing address", "shipping address", "postal address"),
        ("street", "road", "lane", "avenue", "apartment", "flat", "building",
         "block", "district", "nagar", "colony", "sector"),
        _WEAK_GENERIC,
    ),
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


# ---------------------------------------------------------------------------
# ADDRESS scoring (§11). An address is not a single-token pattern — it is a
# *block* of text that must exhibit several independent geographic signals.
# Rather than a brittle regex that flags any sentence containing "road", we
# require a combination: an address label and/or street term, plus a
# corroborating signal (house/building number, PIN/postal code, city/state).
# This keeps unrelated prose ("...drove down the road...") from being flagged.
# ---------------------------------------------------------------------------

# Street / thoroughfare terms.
_ADDR_STREET = (
    "street", "st.", "road", "rd.", "lane", "ln.", "avenue", "ave", "boulevard",
    "blvd", "drive", "marg", "cross", "main road", "highway", "bypass",
)
# Building / unit terms.
_ADDR_UNIT = (
    "apartment", "apartments", "apt", "flat", "building", "block", "tower",
    "villa", "plot", "house no", "door no", "floor", "suite", "unit", "no.",
)
# Locality / administrative terms (generic, plus common Indian locality words).
_ADDR_LOCALITY = (
    "district", "city", "state", "country", "nagar", "colony", "layout",
    "sector", "phase", "extension", "puram", "pura", "ganj", "vihar", "enclave",
    "hills", "park", "market", "town", "village", "taluk", "mandal",
)
# Explicit address labels.
_ADDR_LABEL = (
    "address", "home address", "residential address", "permanent address",
    "office address", "billing address", "shipping address", "postal address",
    "correspondence address",
)
# Postal / PIN code terms.
_ADDR_POSTAL = ("pincode", "pin code", "postal code", "zip code", "zip", "pin")

# A handful of Indian state/UT names that strongly indicate a real address
# block (kept small and deterministic; not an exhaustive gazetteer).
_ADDR_STATES = (
    "tamil nadu", "kerala", "karnataka", "andhra pradesh", "telangana",
    "maharashtra", "gujarat", "rajasthan", "punjab", "haryana", "delhi",
    "west bengal", "uttar pradesh", "madhya pradesh", "bihar", "odisha",
    "assam", "goa", "chandigarh", "jharkhand", "chhattisgarh", "uttarakhand",
    "himachal pradesh", "jammu", "kashmir",
)

# Point weights for the address block model.
_ADDR_W_LABEL = 34
_ADDR_W_STREET = 22
_ADDR_W_UNIT = 16
_ADDR_W_LOCALITY = 14
_ADDR_W_STATE = 20
_ADDR_W_PINCODE = 26          # a 6-digit Indian PIN inside the block
_ADDR_W_HOUSE_NUMBER = 12     # a leading house/plot number
_ADDR_W_MULTILINE = 8         # spans more than one line


@dataclass
class AddressScore:
    confidence: float          # 0..1
    score: float               # 0..100
    signals: list[str] = field(default_factory=list)


def _has_pincode(block: str) -> bool:
    # Indian PIN is 6 digits (optionally split "600 040"); accept a 5-6 digit
    # postal-code-shaped run that is NOT part of a longer number. A phone
    # number (10+ digits, optional +CC) contains 6-digit substrings, so we
    # first strip separators and reject blocks whose largest pure-digit run is
    # phone-length (7+), which would otherwise masquerade as a PIN.
    import re as _re
    # If the block contains a long contiguous numeric identifier (phone / card
    # / Aadhaar), that number is not a postal code.
    for run in _re.findall(r"\d[\d ]*\d", block):
        if sum(c.isdigit() for c in run) >= 7 and " " not in run.strip():
            return False
        # "+91 98765 43210" -> collapsed 12 digits: also phone-like.
        if sum(c.isdigit() for c in run) >= 10:
            return False
    return bool(_re.search(r"(?<!\d)\d{3}\s?\d{3}(?!\d)", block)) or bool(
        _re.search(r"(?<!\d)\d{5,6}(?!\d)", block)
    )


def _has_house_number(block: str) -> bool:
    import re as _re
    # A leading number or "12,", "Flat 302", "No. 45", "12/3" at a line start.
    for line in block.splitlines():
        s = line.strip()
        if _re.match(r"^(?:flat|plot|door|house|no\.?|#)?\s*#?\d{1,4}[a-zA-Z]?\s*[,/\-]", s, _re.I):
            return True
        if _re.match(r"^\d{1,4}[a-zA-Z]?\s*,", s):
            return True
    return False


def score_address(block: str, *, multiline: bool = False) -> AddressScore:
    """Score a candidate address *block* on multiple independent signals.

    ``block`` is the reconstructed text of one or more nearby lines. The score
    combines an address label, street/unit/locality terms, an Indian
    state/PIN, and a leading house number. A single lone signal (e.g. just the
    word "road") is deliberately insufficient to cross the redaction floor.
    """
    norm = _normalize(block)
    signals: list[str] = []
    score = 0.0
    cues = 0

    label = [k for k in _ADDR_LABEL if k in norm]
    if label:
        score += _ADDR_W_LABEL
        cues += 1
        signals.append(f"address label: {label[0]}")

    street = [k for k in _ADDR_STREET if k in norm]
    if street:
        score += _ADDR_W_STREET
        cues += 1
        signals.append(f"street term: {street[0]}")

    unit = [k for k in _ADDR_UNIT if k in norm]
    if unit:
        score += _ADDR_W_UNIT
        cues += 1
        signals.append(f"building/unit term: {unit[0]}")

    locality = [k for k in _ADDR_LOCALITY if k in norm]
    if locality:
        score += _ADDR_W_LOCALITY
        cues += 1
        signals.append(f"locality term: {locality[0]}")

    state = [k for k in _ADDR_STATES if k in norm]
    if state:
        score += _ADDR_W_STATE
        cues += 1
        signals.append("state/region name present")

    postal_label = [k for k in _ADDR_POSTAL if k in norm]
    if _has_pincode(block):
        score += _ADDR_W_PINCODE
        cues += 1
        signals.append("postal/PIN code present")
    elif postal_label:
        score += _ADDR_W_LOCALITY
        cues += 1
        signals.append(f"postal term: {postal_label[0]}")

    if _has_house_number(block):
        score += _ADDR_W_HOUSE_NUMBER
        signals.append("house/plot number present")

    if multiline:
        score += _ADDR_W_MULTILINE
        signals.append("multi-line address block")

    # Corroboration: require at least two independent geographic cues so a lone
    # keyword can never redact. One cue alone is capped well below threshold.
    if cues >= 2:
        signals.append(f"{cues} corroborating address cues")
    else:
        score = min(score, 30.0)

    score = max(0.0, min(100.0, score))
    return AddressScore(confidence=round(score / 100.0, 4),
                        score=round(score, 1), signals=signals)


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
