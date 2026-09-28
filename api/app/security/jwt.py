"""JWT encoding, decoding, and verification utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from api.app.config import get_settings


def create_access_token(
    subject: str,
    role: str,
    user_id: int | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    subject : str
        Subject identifier (username).
    role : str
        User role (e.g. ADMIN, MAINTENANCE_ENGINEER, OPERATOR).
    user_id : int | None, optional
        Unique database ID of the user.
    expires_delta : timedelta | None, optional
        Token validity duration; defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns
    -------
    str
        Encoded and signed JWT string.
    """
    settings = get_settings()
    now = datetime.now(UTC)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if user_id is not None:
        payload["user_id"] = user_id

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Parameters
    ----------
    token : str
        Encoded JWT token to validate.

    Returns
    -------
    dict[str, Any]
        Decoded payload claims.

    Raises
    ------
    jwt.ExpiredSignatureError
        If the token has expired.
    jwt.InvalidTokenError
        If the token signature is invalid, malformed, or missing required claims.
    """
    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={
            "require": ["sub", "role", "exp", "iat"],
            "verify_exp": True,
            "verify_iat": True,
        },
    )

    if not payload.get("sub") or not payload.get("role"):
        raise jwt.InvalidTokenError("Missing required subject or role in token claims.")

    return payload
