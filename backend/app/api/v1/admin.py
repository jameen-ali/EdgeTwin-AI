from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.models.user import User
from app.models.mechanic import Mechanic
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized. Admin role required.")
    return current_user

@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).all()
    return users

@router.post("/users", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = hash_password(payload.password)
    user_id = uuid.uuid4()
    
    new_user = User(
        user_id=user_id,
        name=payload.name,
        email=payload.email,
        password_hash=hashed_password,
        role=payload.role,
        is_active=payload.is_active
    )
    db.add(new_user)
    
    # If mechanic, add to mechanic table too
    if payload.role == "mechanic":
        db.add(Mechanic(mechanic_id=user_id, login_status="OFFLINE"))
        
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
        
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: UUID, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Deactivate instead of hard delete to maintain data integrity in foreign keys
    user.is_active = False
    db.commit()
    return {"status": "success", "message": "User deactivated"}

@router.get("/audit-logs")
def get_audit_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    from app.models.audit_log import AuditLog
    # Join with User to get user name
    results = db.query(AuditLog, User.name).outerjoin(User, AuditLog.user_id == User.user_id).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    total = db.query(AuditLog).count()
    
    items = []
    for log, user_name in results:
        items.append({
            "log_id": str(log.log_id),
            "user_id": str(log.user_id),
            "user_name": user_name or "System",
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "ip_address": log.ip_address
        })
        
    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }
