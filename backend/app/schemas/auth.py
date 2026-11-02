from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import UserRole


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
    )

    password: str = Field(
        min_length=1,
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
    )


class AuthTokenResponse(BaseModel):
    user_id: UUID
    username: str
    role: UserRole

    access_token: str
    refresh_token: str

    token_type: Literal["bearer"] = "bearer"

    refresh_token_expires_at: datetime


class CurrentUserResponse(BaseModel):
    user_id: UUID
    username: str
    role: UserRole
    is_active: bool