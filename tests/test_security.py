from __future__ import annotations

import pytest

from campuscare.security import (
    PasswordValidationError,
    hash_password,
    validate_allowed_email,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    encoded = hash_password("Campus123")
    assert encoded != "Campus123"
    assert verify_password("Campus123", encoded)
    assert not verify_password("Wrong123", encoded)


def test_password_hash_uses_unique_salts() -> None:
    assert hash_password("Campus123") != hash_password("Campus123")


def test_weak_password_rejected() -> None:
    for password in ("password", "12345678", "Short1", ""):
        with pytest.raises(PasswordValidationError):
            hash_password(password)


def test_malformed_password_hash_is_rejected_without_crashing() -> None:
    malformed = (
        "",
        "not-a-hash",
        "pbkdf2_sha256$abc$bad$bad",
        "pbkdf2_sha256$999999999999$YQ==$Yg==",
        "other$600000$YQ==$Yg==",
    )
    assert all(not verify_password("Campus123", value) for value in malformed)


def test_nci_email_validation() -> None:
    assert (
        validate_allowed_email(" Test.Student@Student.NCIRL.ie ", ("student.ncirl.ie",))
        == "test.student@student.ncirl.ie"
    )


@pytest.mark.parametrize(
    "email",
    (
        "person@example.com",
        "@student.ncirl.ie",
        "bad space@student.ncirl.ie",
        ".start@student.ncirl.ie",
        "double..dot@student.ncirl.ie",
        "not-an-email",
    ),
)
def test_invalid_email_rejected(email: str) -> None:
    with pytest.raises(ValueError):
        validate_allowed_email(email, ("student.ncirl.ie",))
