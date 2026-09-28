"""Pydantic schemas for authentication and user accounts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials payload for JWT access token generation."""

    username: str = Field(..., min_length=1, max_length=64, description="User login identifier")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class TokenResponse(BaseModel):
    """OAuth2-compatible Bearer token response."""

    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token scheme (bearer)")
    expires_in: int = Field(..., description="Token validity window in seconds")
    role: str = Field(..., description="Authorized role assigned to the user")
    username: str = Field(..., description="Username of the authenticated subject")


class UserResponse(BaseModel):
    """Authenticated user profile representation."""

    id: int = Field(..., description="Unique database identifier")
    username: str = Field(..., description="Unique login handle")
    role: str = Field(..., description="Role assigned in RBAC policy")
    is_active: bool = Field(..., description="Whether account is currently active")
    created_at: datetime = Field(..., description="Account creation timestamp")
