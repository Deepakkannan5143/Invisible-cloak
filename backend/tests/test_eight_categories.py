"""Unit-level coverage for the eight frontend Protection Settings categories.

These tests exercise the DETECT layer (``detect_text``) and the enabled_types
normalization directly (no OCR required). They assert the multi-signal
behaviour required by the spec:

* every enabled category is detectable with AND without a label,
* disabled categories are never returned,
* the frontend toggle aliases (lowercase / UI labels / "custom") map to the
  canonical backend types,
* address is multi-signal (a lone keyword is not an address),
* custom patterns are honoured and validated safely,
* false-positive numeric labels (order/invoice/product) are suppressed.

All identifiers are synthetic / fake.
"""

from app.pipeline.detectors import compile_custom_patterns, detect_text
from app.pipeline.context import REDACT_THRESHOLD
from app.pipeline.engine import normalize_type, _enabled_set
from app.schemas import ScanRequest, CustomPattern

# --- Synthetic (fake) identifiers ------------------------------------------
AADHAAR = "4829 1736 4926"          # Verhoeff-valid
CARD = "4111 1111 1111 1111"        # Luhn-valid
API_KEY = "sk-test-9fJ2Kd8sLpQw3nZx7Ab1Cd"
EMAIL = "deepak@example.com"
PHONE = "+91 98765 43210"


def _types(text, enabled=None, customs=None):
    return {m.type for m in detect_text(text, enabled, customs)}


def _match(text, dtype, enabled=None, customs=None):
    for m in detect_text(text, enabled, customs):
        if m.type == dtype:
            return m
    return None


# --- Alias / enabled_types normalization (§1, §24) -------------------------

def test_frontend_aliases_normalize_to_canonical_types():
    assert normalize_type("aadhar") == "AADHAAR"
    assert normalize_type("credit_card") == "CREDIT_CARD"
    assert normalize_type("Credit Card") == "CREDIT_CARD"
    assert normalize_type("phone_number") == "PHONE"
    assert normalize_type("api key") == "API_KEY"
    assert normalize_type("custom") == "CUSTOM_PATTERN"
    assert normalize_type("custom_pattern") == "CUSTOM_PATTERN"
    assert normalize_type("EMAIL") == "EMAIL"


def test_enabled_set_maps_ui_toggles():
    req = ScanRequest(
        text="",
        enabled_types=["aadhaar", "credit_card", "api_key", "password",
                       "email", "phone", "address", "custom"],
    )
    enabled = _enabled_set(req)
    assert {"AADHAAR", "CREDIT_CARD", "API_KEY", "PASSWORD", "EMAIL",
            "PHONE", "ADDRESS", "CUSTOM_PATTERN"}.issubset(enabled)
    # The single "Credit Card" toggle also protects debit cards.
    assert "DEBIT_CARD" in enabled


# --- Each category: labelled and unlabelled --------------------------------

def test_aadhaar_labelled_and_bare():
    assert _match(f"Aadhaar Number: {AADHAAR}", "AADHAAR").confidence >= 0.9
    m = _match(AADHAAR, "AADHAAR")
    assert m is not None and m.confidence * 100 >= REDACT_THRESHOLD


def test_credit_card_labelled_and_bare():
    assert _match(f"Credit Card: {CARD}", "CREDIT_CARD").confidence >= 0.9
    assert _match("4111111111111111", "CREDIT_CARD") is not None


def test_api_key_labelled_and_bare():
    assert "API_KEY" in _types(f"API Key: {API_KEY}")
    assert "API_KEY" in _types(API_KEY)


def test_password_requires_context_value_not_label():
    m = _match("Password: MySecret123", "PASSWORD")
    assert m is not None and m.confidence >= 0.9
    # The captured value is the secret, not the word "password".
    assert "password" not in m.value.lower()
    # Prose mentioning the word "password" is not a password value.
    assert "PASSWORD" not in _types("I forgot my password yesterday.")


def test_email_labelled_and_bare():
    assert "EMAIL" in _types(f"Email: {EMAIL}")
    assert "EMAIL" in _types(EMAIL)
    # The word "Email" alone is not an email.
    assert "EMAIL" not in _types("Email us anytime")


def test_phone_high_confidence_with_context():
    m = _match(f"Phone Number: {PHONE}", "PHONE")
    assert m is not None and m.confidence * 100 >= REDACT_THRESHOLD


# --- Address is multi-signal (§11, §17) ------------------------------------

def test_address_block_detected():
    block = "Address:\n12, Anna Nagar Main Road,\nChennai, Tamil Nadu - 600040"
    m = _match(block, "ADDRESS", {"ADDRESS"})
    assert m is not None and m.confidence * 100 >= REDACT_THRESHOLD


def test_address_single_keyword_is_not_an_address():
    # A lone "road"/"city" in prose must not be redacted as an address.
    assert not any(
        m.type == "ADDRESS" and m.confidence * 100 >= REDACT_THRESHOLD
        for m in detect_text("We drove down the road into the city.", {"ADDRESS"})
    )
    assert "ADDRESS" not in _types("Please provide your address", {"ADDRESS"})


def test_address_coexists_with_phone_and_email():
    text = ("Home Address: 12 Example Road, Chennai - 600040. "
            "Phone +91 9876543210 email a@b.com")
    t = _types(text, {"ADDRESS", "PHONE", "EMAIL"})
    assert {"ADDRESS", "PHONE", "EMAIL"}.issubset(t)


# --- Custom patterns (§12) -------------------------------------------------

def test_custom_pattern_regex_match():
    specs = compile_custom_patterns([{"name": "Employee ID", "regex": "EMP-[0-9]{6}"}])
    m = _match("Staff EMP-123456 active", "CUSTOM_PATTERN", {"CUSTOM_PATTERN"}, specs)
    assert m is not None
    assert any("Employee ID" in s for s in m.signals)


def test_custom_pattern_literal_name_match():
    specs = compile_custom_patterns([{"name": "Project Falcon"}])
    assert "CUSTOM_PATTERN" in _types("See Project Falcon roadmap",
                                      {"CUSTOM_PATTERN"}, specs)


def test_custom_pattern_disabled_not_run():
    specs = compile_custom_patterns([{"name": "Employee ID", "regex": "EMP-[0-9]{6}"}])
    # CUSTOM_PATTERN not enabled -> not detected.
    assert "CUSTOM_PATTERN" not in _types("EMP-123456", {"EMAIL"}, specs)


def test_custom_pattern_redos_rejected():
    # Catastrophic-backtracking shape must be dropped, not compiled.
    specs = compile_custom_patterns([{"name": "bad", "regex": "(a+)+$"}])
    assert specs == []


def test_custom_pattern_invalid_regex_skipped():
    specs = compile_custom_patterns([
        {"name": "ok", "regex": "ABC-[0-9]{3}"},
        {"name": "broken", "regex": "([unclosed"},
    ])
    assert len(specs) == 1 and specs[0].name == "ok"


# --- Per-toggle isolation (§26) --------------------------------------------

_MIXED = (
    f"Aadhaar Number: {AADHAAR}\n"
    f"Credit Card: {CARD}\n"
    f"Email: {EMAIL}\n"
    f"Phone Number: {PHONE}\n"
    "Password: MySecret123\n"
    f"API Key: {API_KEY}\n"
    "Home Address: 12 Example Road, Chennai - 600040\n"
)


def test_only_aadhaar_enabled():
    assert _types(_MIXED, {"AADHAAR"}) == {"AADHAAR"}


def test_only_credit_card_enabled():
    assert _types(_MIXED, {"CREDIT_CARD"}) == {"CREDIT_CARD"}


def test_only_email_enabled():
    assert _types(_MIXED, {"EMAIL"}) == {"EMAIL"}


def test_only_password_enabled():
    assert _types(_MIXED, {"PASSWORD"}) == {"PASSWORD"}


def test_only_api_key_enabled():
    assert _types(_MIXED, {"API_KEY"}) == {"API_KEY"}


def test_only_address_enabled():
    assert _types(_MIXED, {"ADDRESS"}) == {"ADDRESS"}


def test_all_eight_enabled_detects_each():
    enabled = {"AADHAAR", "CREDIT_CARD", "API_KEY", "PASSWORD", "EMAIL",
               "PHONE", "ADDRESS", "CUSTOM_PATTERN"}
    specs = compile_custom_patterns([{"name": "Employee ID", "regex": "EMP-[0-9]{6}"}])
    text = _MIXED + "Employee ID: EMP-123456\n"
    t = _types(text, enabled, specs)
    assert {"AADHAAR", "CREDIT_CARD", "API_KEY", "PASSWORD", "EMAIL",
            "PHONE", "ADDRESS", "CUSTOM_PATTERN"}.issubset(t)


# --- False-positive protection (§17) ---------------------------------------

def test_order_invoice_product_ids_not_flagged():
    text = ("Order Number: 123456789012\n"
            "Invoice Number: 987654321098\n"
            "Product ID: 111122223333\n")
    t = {m.type for m in detect_text(text)
         if m.confidence * 100 >= REDACT_THRESHOLD}
    assert "AADHAAR" not in t
    assert "CREDIT_CARD" not in t
    assert "PHONE" not in t
