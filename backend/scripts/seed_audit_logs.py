import sys
import os
import uuid
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import engine, Base, SessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User

def seed_audit_logs():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No users found.")
            return

        actions = [
            ("login", "Auth", ""),
            ("create_user", "User", '{"role": "operator"}'),
            ("update_machine", "Machine", '{"status": "warning"}'),
            ("reallocate_load", "Production", '{"source": "Machine A", "target": "Machine B"}'),
            ("assign_ticket", "Ticket", '{"mechanic_id": "..."}'),
            ("close_ticket", "Ticket", '{"status": "closed"}'),
            ("update_settings", "Settings", '{"threshold": 90}'),
        ]

        now = datetime.now(timezone.utc)
        print("Seeding Audit Logs...")
        for i in range(50):
            u = random.choice(users)
            act = random.choice(actions)
            log = AuditLog(
                user_id=u.user_id,
                action=act[0],
                entity_type=act[1],
                entity_id=str(uuid.uuid4()),
                new_value=act[2],
                timestamp=now - timedelta(hours=random.randint(1, 720)),
                ip_address=f"192.168.1.{random.randint(10, 250)}"
            )
            db.add(log)
        
        db.commit()
        print("Audit logs seeded successfully!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_audit_logs()
