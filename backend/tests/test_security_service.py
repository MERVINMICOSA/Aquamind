import pytest

from app.services.security_service import (
    BCRYPT_MAX_PASSWORD_BYTES,
    BCRYPT_ROUNDS,
    PasswordSecurityError,
    hash_password,
    verify_password,
)


def test_hash_password_returns_bcrypt_hash():
    password_hash = hash_password(
        "AquaMindAdmin123!"
    )

    assert isinstance(
        password_hash,
        str,
    )

    assert password_hash.startswith(
        ("$2a$", "$2b$")
    )


def test_hash_password_uses_configured_cost():
    password_hash = hash_password(
        "AquaMindAdmin123!"
    )

    parts = password_hash.split("$")

    assert int(parts[2]) == BCRYPT_ROUNDS


def test_same_password_produces_different_hashes():
    password = "AquaMindAdmin123!"

    first_hash = hash_password(
        password
    )

    second_hash = hash_password(
        password
    )

    assert first_hash != second_hash


def test_correct_password_verifies():
    password = "AquaMindAdmin123!"

    password_hash = hash_password(
        password
    )

    assert verify_password(
        password,
        password_hash,
    )


def test_incorrect_password_does_not_verify():
    password_hash = hash_password(
        "AquaMindAdmin123!"
    )

    assert not verify_password(
        "WrongPassword123!",
        password_hash,
    )


def test_unicode_password_can_be_hashed_and_verified():
    password = "AquaMind-Admin-2026-ñ"

    password_hash = hash_password(
        password
    )

    assert verify_password(
        password,
        password_hash,
    )


def test_empty_password_is_rejected():
    with pytest.raises(
        PasswordSecurityError,
        match="Password cannot be empty",
    ):
        hash_password("")


def test_verify_rejects_empty_password():
    password_hash = hash_password(
        "AquaMindAdmin123!"
    )

    with pytest.raises(
        PasswordSecurityError,
        match="Password cannot be empty",
    ):
        verify_password(
            "",
            password_hash,
        )


def test_password_over_bcrypt_limit_is_rejected():
    password = (
        "a"
        * (BCRYPT_MAX_PASSWORD_BYTES + 1)
    )

    with pytest.raises(
        PasswordSecurityError,
        match=(
            "Password exceeds bcrypt "
            "maximum length"
        ),
    ):
        hash_password(
            password
        )


def test_invalid_hash_does_not_verify():
    assert not verify_password(
        "AquaMindAdmin123!",
        "not-a-valid-bcrypt-hash",
    )


def test_empty_hash_is_rejected():
    with pytest.raises(
        PasswordSecurityError,
        match="Password hash cannot be empty",
    ):
        verify_password(
            "AquaMindAdmin123!",
            "",
        )