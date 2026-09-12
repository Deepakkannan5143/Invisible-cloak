"""Algorithmic validators used to raise/lower detection confidence.

These are real implementations of the checksum algorithms referenced in the
spec: the Luhn algorithm (payment cards) and the Verhoeff algorithm (Aadhaar).
"""

from __future__ import annotations


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def luhn_check(number: str) -> bool:
    """Return True if ``number`` passes the Luhn checksum.

    Used to validate credit/debit card numbers (and any Luhn-based identifier).
    """
    digits = digits_only(number)
    if len(digits) < 12:  # cards are 13-19; below that it's not a card
        return False
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        d = ord(ch) - 48
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# --- Verhoeff (used by Aadhaar / UIDAI) ------------------------------------

# Multiplication table (d)
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

# Permutation table (p)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 9, 1, 6, 7, 4, 3, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_check(number: str) -> bool:
    """Return True if ``number`` passes the Verhoeff checksum.

    Aadhaar (UIDAI) numbers are 12 digits with a Verhoeff check digit.
    """
    digits = digits_only(number)
    if len(digits) != 12:
        return False
    check = 0
    # process digits right-to-left
    for i, ch in enumerate(reversed(digits)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[i % 8][ord(ch) - 48]]
    return check == 0


def is_valid_ipv4(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (0 <= int(p) <= 255):
            return False
        if len(p) > 1 and p[0] == "0":  # reject leading zeros
            return False
    return True
