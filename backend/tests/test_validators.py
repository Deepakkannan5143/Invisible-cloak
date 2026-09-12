from app.pipeline.validators import is_valid_ipv4, luhn_check, verhoeff_check


def test_luhn_valid():
    assert luhn_check("4111 1111 1111 1111")
    assert luhn_check("4111-1111-1111-1111")


def test_luhn_invalid():
    assert not luhn_check("4111 1111 1111 1112")
    assert not luhn_check("1234")  # too short to be a card


def test_verhoeff_valid_aadhaar():
    assert verhoeff_check("4829 1736 4926")
    assert verhoeff_check("482917364926")


def test_verhoeff_invalid():
    assert not verhoeff_check("4829 1736 4928")
    assert not verhoeff_check("1234")  # wrong length


def test_ipv4():
    assert is_valid_ipv4("192.168.1.10")
    assert not is_valid_ipv4("999.1.1.1")
    assert not is_valid_ipv4("192.168.01.1")  # leading zero
