from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.services.security_service import (
    REFRESH_TOKEN_ENTROPY_BYTES,
    RefreshTokenMaterial,
    RefreshTokenSecurityError,
    create_refresh_token_material,
    generate_refresh_token,
    hash_refresh_token,
    verify_refresh_token_hash,
)


@pytest.fixture(autouse=True)
def configure_refresh_token_settings(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "REFRESH_TOKEN_EXPIRE_DAYS",
        7,
    )


# ============================================================
# TOKEN GENERATION
# ============================================================


def test_generate_refresh_token():
    token = generate_refresh_token()

    assert isinstance(token, str)
    assert token
    assert len(token) >= REFRESH_TOKEN_ENTROPY_BYTES


def test_refresh_tokens_are_unique():
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second


# ============================================================
# TOKEN HASHING
# ============================================================


def test_hash_refresh_token_returns_sha256_hex():
    token = generate_refresh_token()

    token_hash = hash_refresh_token(
        token
    )

    assert isinstance(token_hash, str)
    assert len(token_hash) == 64

    int(
        token_hash,
        16,
    )


def test_same_refresh_token_has_stable_hash():
    token = generate_refresh_token()

    first_hash = hash_refresh_token(
        token
    )

    second_hash = hash_refresh_token(
        token
    )

    assert first_hash == second_hash


def test_different_refresh_tokens_have_different_hashes():
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert (
        hash_refresh_token(first)
        != hash_refresh_token(second)
    )


def test_correct_refresh_token_hash_verifies():
    token = generate_refresh_token()

    token_hash = hash_refresh_token(
        token
    )

    assert verify_refresh_token_hash(
        token,
        token_hash,
    )


def test_wrong_refresh_token_does_not_verify():
    token = generate_refresh_token()

    token_hash = hash_refresh_token(
        token
    )

    wrong_token = generate_refresh_token()

    assert not verify_refresh_token_hash(
        wrong_token,
        token_hash,
    )


# ============================================================
# INPUT VALIDATION
# ============================================================


def test_empty_refresh_token_is_rejected():
    with pytest.raises(
        RefreshTokenSecurityError,
        match="Refresh token cannot be empty",
    ):
        hash_refresh_token("")


def test_empty_refresh_token_hash_is_rejected():
    token = generate_refresh_token()

    with pytest.raises(
        RefreshTokenSecurityError,
        match=(
            "Refresh token hash cannot be empty"
        ),
    ):
        verify_refresh_token_hash(
            token,
            "",
        )


# ============================================================
# TOKEN MATERIAL
# ============================================================


def test_create_refresh_token_material():
    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    material = create_refresh_token_material(
        issued_at=issued_at,
    )

    assert isinstance(
        material,
        RefreshTokenMaterial,
    )

    assert material.token

    assert material.token_hash == (
        hash_refresh_token(
            material.token
        )
    )

    assert material.issued_at == issued_at

    assert material.expires_at == (
        issued_at
        + timedelta(days=7)
    )


def test_refresh_token_material_is_unique():
    first = create_refresh_token_material()
    second = create_refresh_token_material()

    assert first.token != second.token

    assert (
        first.token_hash
        != second.token_hash
    )


def test_naive_refresh_token_issue_time_is_rejected():
    with pytest.raises(
        RefreshTokenSecurityError,
        match=(
            "Refresh token issue time "
            "must be timezone-aware"
        ),
    ):
        create_refresh_token_material(
            issued_at=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
            )
        )


def test_invalid_refresh_token_lifetime_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "REFRESH_TOKEN_EXPIRE_DAYS",
        0,
    )

    with pytest.raises(
        RefreshTokenSecurityError,
        match=(
            "Refresh token lifetime must "
            "be greater than zero"
        ),
    ):
        create_refresh_token_material()