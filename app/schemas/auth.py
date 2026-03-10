"""Authentication schemas: register, login, tokens."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="user", pattern="^(user|practitioner|specialist)$")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires
    user: UserBrief


class UserBrief(BaseModel):
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    role: str
    specialist_id: Optional[int] = None
    practitioner_id: Optional[int] = None

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminResetPasswordRequest(BaseModel):
    """Body for PUT /api/admin/users/{id}/password. Accepts new_password (min 6 chars)."""
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminCreateUserRequest(BaseModel):
    """Body for POST /api/admin/users/create. Admin creates a client/user."""
    email: str = Field(..., min_length=3, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(user|practitioner|admin)$")


class MessageResponse(BaseModel):
    message: str