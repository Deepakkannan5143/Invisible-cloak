from app.pipeline.detectors import detect_text


def _types(text, enabled=None):
    return {m.type for m in detect_text(text, enabled)}


def test_detects_email_and_phone():
    t = _types("Contact me at rahul.sharma@example.com or phone +91 98765 43210")
    assert "EMAIL" in t
    assert "PHONE" in t


def test_valid_card_is_detected():
    # Luhn-valid card, require_valid=True
    assert "CREDIT_CARD" in _types("Card No 4111 1111 1111 1111")


def test_invalid_card_is_rejected():
    assert "CREDIT_CARD" not in _types("Card 4111 1111 1111 1112")


def test_aadhaar_confidence_rises_with_valid_checksum():
    valid = detect_text("Aadhaar 4829 1736 4926")
    invalid = detect_text("Aadhaar 4829 1736 4928")
    v = next(m for m in valid if m.type == "AADHAAR")
    iv = next(m for m in invalid if m.type == "AADHAAR")
    assert v.confidence > iv.confidence


def test_api_key_and_token_and_secret():
    text = (
        "OPENAI_API_KEY=sk-live-9fJ2Kd8sLpQw3nZx7Ab1Cd4Ef6Gh0Ij\n"
        "token ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8\n"
        "password: Sunsh1ne@2026!"
    )
    t = _types(text)
    assert "API_KEY" in t
    assert "ACCESS_TOKEN" in t
    assert "PASSWORD" in t


def test_aws_key_and_private_key():
    t = _types("AKIAIOSFODNN7EXAMPLE\n-----BEGIN PRIVATE KEY-----")
    assert "AWS_ACCESS_KEY" in t
    assert "PRIVATE_KEY" in t


def test_pan_and_ssn():
    t = _types("PAN ABCDE1234F and SSN 123-45-6789")
    assert "PAN" in t
    assert "SSN" in t


def test_ip_valid_only():
    assert "IP_ADDRESS" in _types("server 192.168.1.10")
    assert "IP_ADDRESS" not in _types("version 999.1.1.1")


def test_enabled_filter():
    t = _types("email a@b.com card 4111 1111 1111 1111", enabled={"EMAIL"})
    assert t == {"EMAIL"}


def test_context_scoring_raises_confidence():
    with_ctx = detect_text("password: hunter2xyz")
    pw = next(m for m in with_ctx if m.type == "PASSWORD")
    assert pw.confidence >= 0.9
