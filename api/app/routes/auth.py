"""Authentication and user profile endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.config import get_settings
from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from api.app.schemas.common import ProblemDetails
from api.app.security.audit import log_security_event
from api.app.security.deps import get_current_user
from api.app.security.jwt import create_access_token
from api.app.security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])

DbDep = Annotated[Session, Depends(get_db)]
settings = get_settings()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT access token",
    description="Validate username/password credentials and return a signed Bearer token with RBAC role claims.",
    responses={
        401: {"model": ProblemDetails, "description": "Invalid credentials or inactive account"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def login(
    payload: LoginRequest,
    db: DbDep,
) -> TokenResponse:
    """Validate credentials and issue JWT access token."""
    user = db.execute(
        select(UserRecord).where(UserRecord.username == payload.username)
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        log_security_event(
            action="LOGIN",
            user=payload.username,
            role=getattr(user, "role", None),
            success=False,
            details={"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_security_event(
            action="LOGIN",
            user=user.username,
            role=user.role,
            success=False,
            details={"reason": "account_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user.username,
        role=user.role,
        user_id=user.id,
    )

    log_security_event(
        action="LOGIN",
        user=user.username,
        role=user.role,
        success=True,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        username=user.username,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
    description="Retrieve account details and role permissions of the currently authenticated subject.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated or invalid token"},
    },
)
def get_me(
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> UserResponse:
    """Return profile details for the authenticated subject."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
