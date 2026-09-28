"""Role definitions and permission constants for Role-Based Access Control (RBAC)."""

from enum import Enum


class UserRole(str, Enum):
    """Canonical application roles defined for EdgeTwin AI."""

    ADMIN = "ADMIN"
    MAINTENANCE_ENGINEER = "MAINTENANCE_ENGINEER"
    OPERATOR = "OPERATOR"


# Role hierarchy and capability sets
ROLE_CAPABILITIES: dict[UserRole, set[str]] = {
    UserRole.ADMIN: {
        "fleet:read",
        "telemetry:read",
        "twin:read",
        "predictions:read",
        "alerts:read",
        "alerts:write",
        "maintenance:read",
        "maintenance:write",
        "feedback:write",
        "scenarios:control",
        "system:admin",
    },
    UserRole.MAINTENANCE_ENGINEER: {
        "fleet:read",
        "telemetry:read",
        "twin:read",
        "predictions:read",
        "alerts:read",
        "alerts:write",
        "maintenance:read",
        "maintenance:write",
        "feedback:write",
        "scenarios:control",
    },
    UserRole.OPERATOR: {
        "fleet:read",
        "telemetry:read",
        "twin:read",
        "predictions:read",
        "alerts:read",
        "feedback:write",
    },
}

ALL_AUTHENTICATED_ROLES: set[UserRole] = {
    UserRole.ADMIN,
    UserRole.MAINTENANCE_ENGINEER,
    UserRole.OPERATOR,
}

PRIVILEGED_MAINTENANCE_ROLES: set[UserRole] = {
    UserRole.ADMIN,
    UserRole.MAINTENANCE_ENGINEER,
}

ADMIN_ONLY_ROLES: set[UserRole] = {
    UserRole.ADMIN,
}
