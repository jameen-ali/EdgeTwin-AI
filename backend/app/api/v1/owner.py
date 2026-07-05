from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.cost_log import CostLog
from app.models.machine import Machine
from app.models.ticket import Ticket, TicketStatus
from app.models.alert import Alert

router = APIRouter()


@router.get("/expenses")
def get_expenses(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    range: str = "month"
):
    """Get expense summaries grouped by month or year."""
    if range == "year":
        results = db.query(
            CostLog.year.label("year"),
            func.sum(CostLog.amount).label("total_cost"),
            func.count(CostLog.cost_id).label("ticket_count"),
        ).group_by(CostLog.year).order_by(CostLog.year.asc()).all()
    else:
        results = db.query(
            CostLog.year.label("year"),
            CostLog.month.label("month"),
            func.sum(CostLog.amount).label("total_cost"),
            func.count(CostLog.cost_id).label("ticket_count"),
        ).group_by(CostLog.year, CostLog.month).order_by(CostLog.year.asc(), CostLog.month.asc()).all()

    items = []
    for r in results:
        period_str = str(r.year) if range == "year" else f"{r.year}-{r.month:02d}"
        items.append({
            "period": period_str,
            "total_cost": round(r.total_cost or 0, 2),
            "ticket_count": r.ticket_count or 0,
            "avg_repair_time": 2.5,
            "machines": []
        })
    return items


@router.get("/stats")
def get_factory_stats(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """High-level factory statistics for the owner executive dashboard."""
    total_machines = db.query(func.count(Machine.machine_id)).scalar() or 0
    avg_health = db.query(func.avg(Machine.health_score)).scalar() or 0
    critical_count = db.query(func.count(Machine.machine_id)).filter(Machine.status == "critical").scalar() or 0
    warning_count = db.query(func.count(Machine.machine_id)).filter(Machine.status == "warning").scalar() or 0
    normal_count = db.query(func.count(Machine.machine_id)).filter(Machine.status == "normal").scalar() or 0
    total_alerts = db.query(func.count(Alert.alert_id)).scalar() or 0
    open_tickets = db.query(func.count(Ticket.ticket_id)).filter(
        Ticket.status.notin_([TicketStatus.closed, TicketStatus.reviewed])
    ).scalar() or 0
    total_cost_ytd = db.query(func.sum(CostLog.amount)).scalar() or 0

    return {
        "total_machines": total_machines,
        "active_machines": normal_count,
        "critical_machines": critical_count,
        "overall_health_score": round(avg_health, 1),
        "total_alerts": total_alerts,
        "active_tickets": open_tickets,
        "machines_operational": normal_count,
        "machines_warning": warning_count,
        "machines_critical": critical_count,
        "overall_uptime_percent": round(94.7 if avg_health > 50 else 78.2, 1),
        "total_maintenance_cost_ytd": round(total_cost_ytd, 2),
        "avg_health_score": round(avg_health, 1),
        "open_tickets": open_tickets,
        "mttr_hours": 2.8,
        "mtbf_hours": 720
    }


@router.get("/impact")
def get_production_impact(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get production impact data per machine."""
    machines = db.query(Machine).all()
    items = []
    for m in machines:
        # Calculate downtime based on health score
        downtime_multiplier = max(0, (100 - m.health_score) / 10)
        production_loss = max(0, (100 - m.health_score) * 0.2)
        items.append({
            "machine_id": str(m.machine_id),
            "machine_name": m.name,
            "downtime_hours": round(downtime_multiplier * 4, 1),
            "production_loss_percent": round(production_loss, 1),
            "risk_level": m.risk_level.value if hasattr(m.risk_level, 'value') else str(m.risk_level)
        })
    return items
