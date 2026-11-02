from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    require_admin,
)
from app.db.enums import UserRole
from app.models.system import User


pytestmark = pytest.mark.asyncio


async def test_require_admin_returns_admin_user():
    user = User(
        id=uuid4(),
        username="admin",
        password_hash="test-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    result = await require_admin(
        current_user=user
    )

    assert result is user


async def test_require_admin_rejects_non_admin_role():
    user = SimpleNamespace(
        role="non-admin",
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        await require_admin(
            current_user=user
        )

    assert (
        exc_info.value.status_code
        == 403
    )

    assert (
        exc_info.value.detail
        == "Administrator access required"
    )