"""Password hashing and verification utilities using bcrypt."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with a generated salt.

    Parameters
    ----------
    password : str
        Plaintext password to hash.

    Returns
    -------
    str
        Securely hashed password string.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")

    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches an existing bcrypt hash.

    Parameters
    ----------
    plain_password : str
        Plaintext password to test.
    hashed_password : str
        Stored bcrypt hash.

    Returns
    -------
    bool
        True if the password matches the hash, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
    except Exception:  # noqa: BLE001
        return False
