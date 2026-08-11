from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_vietnamese_address_is_case_insensitive_and_hides_value() -> None:
    out = scrub_text("Địa chỉ: 12 Đường Láng, Quận Đống Đa")
    assert "Láng" not in out
    assert "Đống Đa" not in out
    assert "REDACTED_ADDRESS_VN" in out


def test_scrub_passport() -> None:
    out = scrub_text("Passport C1234567 expires soon")
    assert "C1234567" not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_credit_card_and_cccd() -> None:
    assert "4111 1111 1111 1111" not in scrub_text("card 4111 1111 1111 1111")
    assert "REDACTED_CCCD" in scrub_text("cccd 123456789012")
