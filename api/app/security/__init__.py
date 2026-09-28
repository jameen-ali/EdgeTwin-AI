"""Security and access control package."""

from api.app.security.audit import log_security_event
from api.app.security.deps import (
    get_current_user,
    get_current_ws_user,
    require_role,
    require_roles,
)
from api.app.security.jwt import create_access_token, decode_access_token
from api.app.security.passwords import hash_password, verify_password
from api.app.security.roles import (
    ADMIN_ONLY_ROLES,
    ALL_AUTHENTICATED_ROLES,
    PRIVILEGED_MAINTENANCE_ROLES,
    ROLE_CAPABILITIES,
    UserRole,
)

__all__ = [
    "ADMIN_ONLY_ROLES",
    "ALL_AUTHENTICATED_ROLES",
    "PRIVILEGED_MAINTENANCE_ROLES",
    "ROLE_CAPABILITIES",
    "UserRole",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_current_ws_user",
    "hash_password",
    "log_security_event",
    "require_role",
    "require_roles",
    "verify_password",
]
