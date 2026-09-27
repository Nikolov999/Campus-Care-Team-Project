from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re

PBKDF2_ITERATIONS = 600_000
MIN_PBKDF2_ITERATIONS = 100_000
MAX_PBKDF2_ITERATIONS = 2_000_000
SALT_BYTES = 16
DIGEST_BYTES = 32
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")
EMAIL_LOCAL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")


class PasswordValidationError(ValueError):
    pass


def validate_password(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise PasswordValidationError(
            "Password must be 8-128 characters and include at least one letter and one number."
        )


def hash_password(password: str) -> str:
    validate_password(password)
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=PBKDF2_ITERATIONS,
        salt=base64.urlsafe_b64encode(salt).decode("ascii"),
        digest=base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        if not MIN_PBKDF2_ITERATIONS <= iterations <= MAX_PBKDF2_ITERATIONS:
            return False
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
        if len(salt) != SALT_BYTES or len(expected) != DIGEST_BYTES:
            return False
    except (ValueError, TypeError, binascii.Error, OverflowError, AttributeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def normalise_email(email: str) -> str:
    return email.strip().lower()


def validate_allowed_email(email: str, allowed_domains: tuple[str, ...]) -> str:
    normalised = normalise_email(email)
    if len(normalised) > 254 or normalised.count("@") != 1:
        raise ValueError("Enter a valid email address.")

    local_part, domain = normalised.rsplit("@", 1)
    if (
        not local_part
        or len(local_part) > 64
        or not EMAIL_LOCAL_PATTERN.fullmatch(local_part)
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
    ):
        raise ValueError("Enter a valid email address.")

    if domain not in allowed_domains:
        allowed = ", ".join(f"@{item}" for item in allowed_domains)
        raise ValueError(f"Registration is limited to NCI email domains: {allowed}.")
    return normalised
