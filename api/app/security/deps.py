"""FastAPI security dependencies for authentication, RBAC, and WebSocket guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Query, WebSocket, status
from fastapi.exceptions import WebSocketException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.config import get_settings
from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.security.audit import log_security_event
from api.app.security.jwt import decode_access_token
from api.app.security.roles import UserRole

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> UserRecord:
    """Extract and validate the currently authenticated user from the HTTP Bearer token.

    Parameters
    ----------
    db : Session
        Database session.
    bearer_token : str | None
        Token parsed from the Authorization header by oauth2_scheme.
    authorization : str | None
        Raw Authorization header fallback.

    Returns
    -------
    UserRecord
        Active authenticated user database entity.

    Raises
    ------
    HTTPException (401)
        If token is missing, expired, invalid, or user is inactive/unknown.
    """
    token: str | None = bearer_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        log_security_event(
            "AUTH_FAILURE", user=None, role=None, success=False, details={"reason": "token_expired"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        log_security_event(
            "AUTH_FAILURE", user=None, role=None, success=False, details={"reason": "invalid_token"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    username: str = payload["sub"]
    user = db.execute(
        select(UserRecord).where(UserRecord.username == username)
    ).scalar_one_or_none()

    if user is None:
        log_security_event(
            "AUTH_FAILURE",
            user=username,
            role=None,
            success=False,
            details={"reason": "user_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_security_event(
            "AUTH_FAILURE",
            user=username,
            role=user.role,
            success=False,
            details={"reason": "user_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(
    allowed_roles: set[UserRole | str] | list[UserRole | str],
) -> Callable[[UserRecord], UserRecord]:
    """Dependency factory enforcing that the authenticated user possesses one of the allowed roles.

    Parameters
    ----------
    allowed_roles : set or list of UserRole or str
        Permitted roles for the target route.

    Returns
    -------
    Callable[[UserRecord], UserRecord]
        FastAPI dependency checking user.role.
    """
    normalized_roles = {r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles}

    def _role_checker(
        current_user: Annotated[UserRecord, Depends(get_current_user)],
    ) -> UserRecord:
        if current_user.role not in normalized_roles:
            log_security_event(
                action="RBAC_DENIED",
                user=current_user.username,
                role=current_user.role,
                success=False,
                details={"allowed_roles": list(normalized_roles)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: User role '{current_user.role}' lacks permission for this action.",
            )
        return current_user

    return _role_checker


def require_role(role: UserRole | str) -> Callable[[UserRecord], UserRecord]:
    """Dependency helper enforcing a single required role."""
    return require_roles({role})


async def get_current_ws_user(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Query(description="JWT access token")] = None,
) -> UserRecord:
    """Extract and validate the authenticated user establishing a WebSocket connection.

    Accepts token via query parameter ?token=<jwt> or Authorization header.
    Rejects with WebSocket close code 1008 (Policy Violation) if unauthenticated.
    """
    effective_token = token
    if not effective_token:
        # Check header
        auth_hdr = websocket.headers.get("authorization")
        if auth_hdr and auth_hdr.lower().startswith("bearer "):
            effective_token = auth_hdr[7:].strip()

    if not effective_token:
        log_security_event(
            action="WS_AUTH_REJECTED",
            user=None,
            role=None,
            target=str(websocket.url.path),
            success=False,
            details={"reason": "missing_token"},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token is required for WebSocket connection.",
        )

    try:
        payload = decode_access_token(effective_token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        log_security_event(
            action="WS_AUTH_REJECTED",
            user=None,
            role=None,
            target=str(websocket.url.path),
            success=False,
            details={"reason": "invalid_or_expired_token"},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token.",
        ) from exc

    username: str = payload["sub"]
    user = db.execute(
        select(UserRecord).where(UserRecord.username == username)
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        log_security_event(
            action="WS_AUTH_REJECTED",
            user=username,
            role=getattr(user, "role", None),
            target=str(websocket.url.path),
            success=False,
            details={"reason": "inactive_or_not_found"},
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found or account is deactivated.",
        )

    log_security_event(
        action="WS_AUTH_SUCCESS",
        user=user.username,
        role=user.role,
        target=str(websocket.url.path),
        success=True,
    )
    return user
