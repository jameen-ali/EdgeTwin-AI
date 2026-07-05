from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    import uuid
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id_uuid = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id_uuid, User.is_active).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole):
    """
    FastAPI dependency factory for role-based access control.
    Usage: Depends(require_roles(UserRole.admin, UserRole.maintenance_manager))
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _check


# Pre-built role dependencies for convenience
CurrentUser      = Annotated[User, Depends(get_current_user)]
AdminOnly        = Annotated[User, Depends(require_roles(UserRole.admin))]
OperatorOnly     = Annotated[User, Depends(require_roles(UserRole.operator))]
MechanicOnly     = Annotated[User, Depends(require_roles(UserRole.mechanic))]
ManagerOnly      = Annotated[User, Depends(require_roles(UserRole.maintenance_manager))]
ProductionOnly   = Annotated[User, Depends(require_roles(UserRole.production_manager))]
OwnerOnly        = Annotated[User, Depends(require_roles(UserRole.factory_owner))]
ManagerOrOwner   = Annotated[User, Depends(require_roles(
    UserRole.maintenance_manager, UserRole.factory_owner
))]
