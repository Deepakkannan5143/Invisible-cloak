"""Explicit card-detector tests (TEST 1-7 from the debugging spec).

These prove the detector works independently of the frontend, exercising both
the raw-text path (``detect_text``) and the spatial OCR-token path (``locate``),
including cards split / merged across OCR tokens. All identifiers are synthetic.

Regression guard: the fix that broadened cross-line reconstruction to accept
OCR-merged 8-digit groups must not resurrect false positives (random numbers
that fail Luhn) and must not disturb Aadhaar (Verhoeff) detection.
"""

from app.pipeline.detectors import detect_text
from app.pipeline.locate import Box, Token, locate
from app.pipeline.context import REDACT_THRESHOLD

# Synthetic (fake) test identifiers.
CARD_4111 = "4111 1111 1111 1111"   # Luhn-valid
CARD_5555 = "5555 5555 5555 4444"   # Luhn-valid
RANDOM_16 = "1234567890123456"      # fails Luhn
VALID_AADHAAR = "4829 1736 4926"    # Verhoeff-valid


def _tok(text, x, y, w=45, h=20):
    return Token(text, Box(x, y, w, h))


def _types_text(text):
    return {m.type: m for m in detect_text(text)}


def _redacts(dets, dtype):
    for d in dets:
        t = getattr(d, "type", None) or getattr(d, "detectedType", None)
        conf = d.confidence
        if t == dtype and conf * 100.0 >= REDACT_THRESHOLD:
            return True
    return False


# --- TEST 1: label + card split into 4 OCR tokens (same line) --------------

def test_1_tokens_debit_card_number_split():
    tokens = [
        _tok("Debit", 10, 50, 50), _tok("Card", 65, 50, 45),
        _tok("Number", 115, 50, 60),
        _tok("4111", 180, 50), _tok("1111", 230, 50),
        _tok("1111", 280, 50), _tok("1111", 330, 50),
    ]
    dets = locate(tokens, None, 500, 300)
    cards = [d for d in dets if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    assert cards[0].confidence >= 0.9
    assert "strong validation passed" in cards[0].signals


# --- TEST 2: labelled card in text -----------------------------------------

def test_2_credit_card_with_label_text():
    m = _types_text(f"Credit Card: {CARD_5555}").get("CREDIT_CARD")
    assert m is not None and m.confidence >= 0.9


# --- TEST 3: bare card number, no label (Luhn passes) ----------------------

def test_3_bare_card_number_luhn():
    m = _types_text("4111111111111111").get("CREDIT_CARD")
    assert m is not None
    assert m.confidence * 100.0 >= REDACT_THRESHOLD


# --- TEST 4: split OCR tokens, no label -> ONE unioned bbox -----------------

def test_4_split_tokens_single_union_box():
    tokens = [
        _tok("4111", 10, 50), _tok("1111", 60, 50),
        _tok("1111", 110, 50), _tok("1111", 160, 50),
    ]
    dets = locate(tokens, None, 500, 300)
    cards = [d for d in dets if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    box = cards[0].box
    # One union box spanning all four tokens (~x 10..205).
    assert box.x <= 12 and box.x + box.w >= 200


def test_4b_card_merged_8plus8_across_lines():
    # OCR frequently merges two 4-digit groups into an 8-digit token; a card
    # split as 8+8 across two lines must still reconstruct (the bug this fixes).
    tokens = [_tok("41111111", 10, 50, 90), _tok("11111111", 10, 80, 90)]
    cards = [d for d in locate(tokens, None, 500, 300) if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    assert cards[0].box.h > 40  # union spans both lines


# --- TEST 5: random 16-digit number, fails Luhn -> not a card --------------

def test_5_random_number_not_card():
    assert "CREDIT_CARD" not in _types_text(RANDOM_16)
    # Even split across tokens it must not be resurrected as a card.
    tokens = [_tok("12345678", 10, 50, 90), _tok("90123456", 10, 80, 90)]
    assert not any(d.type == "CREDIT_CARD" for d in locate(tokens, None, 500, 300))


# --- TEST 6: CVV only with card/payment context ----------------------------

def test_6_cvv_requires_context():
    # "CVV: 482" carries its own card label -> detected.
    assert "CVV" in _types_text("CVV: 482")
    # Near a full card it is at least as confident.
    with_card = _types_text(f"Credit Card {CARD_4111} CVV: 482")
    assert "CVV" in with_card
    # A bare 3-digit number with no CVV/card context is NOT a CVV.
    assert "CVV" not in _types_text("Room 482 floor 9")


# --- TEST 7: Aadhaar regression --------------------------------------------

def test_7_aadhaar_still_detected():
    m = _types_text(f"Aadhaar Number: {VALID_AADHAAR}").get("AADHAAR")
    assert m is not None and m.confidence >= 0.9


def test_7b_aadhaar_not_confused_with_card_and_vice_versa():
    # 12-digit Aadhaar is not a card; 16-digit card is not Aadhaar.
    aadhaar = _types_text(f"Aadhaar Number: {VALID_AADHAAR}")
    card = _types_text(f"Credit Card: {CARD_4111}")
    assert "AADHAAR" in aadhaar and "CREDIT_CARD" not in aadhaar
    assert "CREDIT_CARD" in card and "AADHAAR" not in card
