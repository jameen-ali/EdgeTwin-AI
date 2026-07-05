from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.mechanic import Mechanic
from app.models.user import User
from app.schemas.mechanic import MechanicResponse, MechanicUpdate

router = APIRouter()

@router.get("", response_model=List[MechanicResponse])
def get_mechanics(db: Session = Depends(get_db)):
    # Join Mechanic with User to get name and email
    results = db.query(Mechanic, User).join(User, Mechanic.mechanic_id == User.user_id).all()
    mechanics = []
    for m, u in results:
        m_dict = {c.name: getattr(m, c.name) for c in m.__table__.columns}
        m_dict["name"] = u.name
        m_dict["email"] = u.email
        mechanics.append(MechanicResponse(**m_dict))
    return mechanics

@router.get("/{mechanic_id}", response_model=MechanicResponse)
def get_mechanic(mechanic_id: UUID, db: Session = Depends(get_db)):
    result = db.query(Mechanic, User).join(User, Mechanic.mechanic_id == User.user_id).filter(Mechanic.mechanic_id == mechanic_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Mechanic not found")
    m, u = result
    m_dict = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    m_dict["name"] = u.name
    m_dict["email"] = u.email
    return MechanicResponse(**m_dict)

@router.put("/{mechanic_id}/status", response_model=MechanicResponse)
def update_mechanic_status(mechanic_id: UUID, payload: MechanicUpdate, db: Session = Depends(get_db)):
    result = db.query(Mechanic, User).join(User, Mechanic.mechanic_id == User.user_id).filter(Mechanic.mechanic_id == mechanic_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Mechanic not found")
    m, u = result
    
    if payload.login_status is not None:
        m.login_status = payload.login_status
    if payload.current_assignment_id is not None:
        m.current_assignment_id = payload.current_assignment_id
        
    db.commit()
    db.refresh(m)

    m_dict = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    m_dict["name"] = u.name
    m_dict["email"] = u.email
    return MechanicResponse(**m_dict)
