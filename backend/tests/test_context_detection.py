"""Context-aware detection tests (unit level, no OCR required).

Covers the required scenarios: labelled and unlabelled Aadhaar, Luhn cards,
CVV/expiry near card context, negative-context suppression (order/invoice/
account numbers), random numbers/dates, and PAN with/without context. These
assert on the confidence model + redaction threshold, not just presence.

All identifiers are synthetic/fake.
"""

from app.pipeline.detectors import detect_text
from app.pipeline.context import (
    REDACT_THRESHOLD,
    score_candidate,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)

# Synthetic identifiers (fake).
VALID_AADHAAR = "4829 1736 4926"       # passes Verhoeff
UNVERIFIED_AADHAAR = "2345 6789 0123"  # fails Verhoeff (illustrative)
VALID_CARD = "5264 1234 5678 0006"     # passes Luhn
INVALID_CARD = "5264 1234 5678 9012"   # fails Luhn


def _by_type(text):
    return {m.type: m for m in detect_text(text)}


def _would_redact(text, dtype):
    m = _by_type(text).get(dtype)
    return m is not None and m.confidence * 100.0 >= REDACT_THRESHOLD


# --- 1. Aadhaar with label --------------------------------------------------

def test_aadhaar_with_label_is_detected_and_redacted():
    assert _would_redact(f"Aadhaar Number: {UNVERIFIED_AADHAAR}", "AADHAAR")


# --- 2. Aadhaar without label (structural) ---------------------------------

def test_valid_aadhaar_without_label_still_detected():
    m = _by_type(VALID_AADHAAR).get("AADHAAR")
    assert m is not None
    assert "strong validation passed" in m.signals
    assert m.confidence * 100.0 >= REDACT_THRESHOLD


# --- 3 & 4. Debit / credit card with label ---------------------------------

def test_debit_card_with_label():
    m = _by_type(f"Debit Card Number: {VALID_CARD}").get("CREDIT_CARD")
    assert m is not None and m.confidence >= 0.9
    assert "strong validation passed" in m.signals


def test_credit_card_with_label():
    assert _would_redact(f"Credit Card: {VALID_CARD}", "CREDIT_CARD")


# --- 6. CVV near card context ----------------------------------------------

def test_cvv_near_card_context_detected():
    text = f"Debit Card Number: {VALID_CARD}  CVV: 482  Expiry: 09/29"
    types = _by_type(text)
    assert "CVV" in types and types["CVV"].confidence * 100 >= REDACT_THRESHOLD
    assert "CARD_EXPIRY" in types
    assert "CREDIT_CARD" in types


# --- 7. random 3-digit number without context ------------------------------

def test_random_three_digit_not_flagged_as_cvv():
    types = _by_type("Room 482 on floor 9")
    assert "CVV" not in types


def test_random_date_not_flagged_as_expiry():
    types = _by_type("Meeting on 09/29 at noon")
    assert "CARD_EXPIRY" not in types


# --- 8. random 12-digit without Aadhaar context ----------------------------

def test_unverified_bare_12_digits_not_redacted():
    # Fails Verhoeff and has no Aadhaar context -> below threshold.
    assert not _would_redact(UNVERIFIED_AADHAAR, "AADHAAR")


# --- 9 & 10. Order / Invoice numbers (negative context) --------------------

def test_order_number_not_redacted():
    assert not _would_redact("Order Number: 123456789012", "AADHAAR")


def test_invoice_number_not_redacted():
    assert not _would_redact("Invoice Number: 123456789012", "AADHAAR")


# --- 11. Account number (contextual, not blind Aadhaar) --------------------

def test_account_number_not_treated_as_aadhaar():
    # "Account Number: 123456789012" must not become a high-confidence Aadhaar.
    m = _by_type("Account Number: 123456789012").get("AADHAAR")
    assert m is None or m.confidence * 100.0 < REDACT_THRESHOLD


# --- 12. PAN with and without context --------------------------------------

def test_pan_with_and_without_context():
    with_ctx = _by_type("PAN: ABCDE1234F").get("PAN")
    without_ctx = _by_type("ABCDE1234F").get("PAN")
    assert with_ctx is not None and without_ctx is not None
    # Context should not lower confidence.
    assert with_ctx.confidence >= without_ctx.confidence


# --- 13. Multiple sensitive values in one string ---------------------------

def test_multiple_sensitive_values():
    text = (
        f"Aadhaar Number: {VALID_AADHAAR}\n"
        f"Credit Card: {VALID_CARD}\n"
        "Email: person@example.com\n"
        "password: Sunsh1ne@2026!"
    )
    types = _by_type(text)
    assert {"AADHAAR", "CREDIT_CARD", "EMAIL", "PASSWORD"}.issubset(types.keys())


# --- Invalid card is rejected (Luhn) ---------------------------------------

def test_invalid_card_rejected_by_luhn():
    types = _by_type(f"Card: {INVALID_CARD}")
    assert "CREDIT_CARD" not in types


# --- Confidence model direct checks ----------------------------------------

def test_score_model_negative_context_suppresses_generic_numeric():
    s = score_candidate(
        "AADHAAR", pattern_matched=True, validated=False,
        context_window="Order Number 123456789012", adjacent=True,
        is_bare_numeric=True,
    )
    assert s.suppressed is True
    assert s.confidence * 100.0 < REDACT_THRESHOLD


def test_score_model_strong_context_and_validation_is_high():
    s = score_candidate(
        "CREDIT_CARD", pattern_matched=True, validated=True,
        context_window="Debit Card Number", adjacent=True,
    )
    assert s.confidence * 100.0 >= HIGH_CONFIDENCE_THRESHOLD
    assert any("strong context" in sig for sig in s.signals)


def test_thresholds_ordered():
    assert HIGH_CONFIDENCE_THRESHOLD > MEDIUM_CONFIDENCE_THRESHOLD


def test_signals_never_contain_raw_value():
    # Signals are generic phrases; ensure the raw value never leaks into them.
    for m in detect_text(f"Aadhaar Number: {VALID_AADHAAR}"):
        for sig in m.signals:
            assert VALID_AADHAAR not in sig
            assert VALID_AADHAAR.replace(" ", "") not in sig
