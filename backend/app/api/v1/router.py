from fastapi import APIRouter
from app.api.v1 import auth, machines, alerts, tickets, mechanics, production, owner, admin

api_router = APIRouter()

api_router.include_router(auth.router,       prefix="/auth",       tags=["Auth"])
api_router.include_router(machines.router,   prefix="/machines",   tags=["Machines"])
api_router.include_router(alerts.router,     prefix="/alerts",     tags=["Alerts"])
api_router.include_router(tickets.router,    prefix="/tickets",    tags=["Tickets"])
api_router.include_router(mechanics.router,  prefix="/mechanics",  tags=["Mechanics"])
api_router.include_router(production.router, prefix="/production", tags=["Production"])
api_router.include_router(owner.router,      prefix="/owner",      tags=["Owner"])
api_router.include_router(admin.router,      prefix="/admin",      tags=["Admin"])
