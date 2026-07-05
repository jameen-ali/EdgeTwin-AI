"""
EdgeTwin AI — Database Seeder
==============================
Seeds all demo users for all 6 roles.
Run with:  python -m app.seeds.seed_users
Or:        python backend/app/seeds/seed_users.py

The seeder is IDEMPOTENT — safe to run multiple times.
Existing users with the same email are skipped (not overwritten).
"""

import sys
import os
import uuid
from datetime import datetime, timezone

# Allow running as a standalone script from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ─── Demo user definitions ────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "name":     "Alex Morgan",
        "email":    "operator@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "operator",
    },
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000002")),
        "name":     "Sarah Chen",
        "email":    "manager@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "maintenance_manager",
    },
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000003")),
        "name":     "Raj Patel",
        "email":    "technician@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "mechanic",
    },
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000004")),
        "name":     "Diana Osei",
        "email":    "production@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "production_manager",
    },
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000005")),
        "name":     "Marcus Liu",
        "email":    "owner@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "factory_owner",
    },
    {
        "user_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000006")),
        "name":     "System Admin",
        "email":    "admin@edgetwin.ai",
        "password": "EdgeTwin@2026",
        "role":     "admin",
    },
]

DEMO_MECHANIC_PROFILES = [
    {
        "mechanic_id":  str(uuid.UUID("00000000-0000-0000-0000-000000000003")),
        "skill_type":   "Electrical & Mechanical",
        "login_status": "available",
        "shift":        "Morning",
        "contact":      "+1-555-0103",
    }
]

DEMO_MACHINES = [
    {
        "machine_id":   str(uuid.UUID("00000000-0000-0000-0001-000000000001")),
        "name":         "CNC Mill #1",
        "location":     "Plant A — Bay 1",
        "type":         "CNC Milling Machine",
        "assigned_operator_id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "health_score": 87.5,
        "risk_level":   "low",
        "rul_hours":    1240.0,
        "status":       "normal",
    },
    {
        "machine_id":   str(uuid.UUID("00000000-0000-0000-0001-000000000002")),
        "name":         "Conveyor Belt #3",
        "location":     "Plant A — Bay 3",
        "type":         "Conveyor System",
        "assigned_operator_id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "health_score": 63.2,
        "risk_level":   "medium",
        "rul_hours":    480.0,
        "status":       "warning",
    },
    {
        "machine_id":   str(uuid.UUID("00000000-0000-0000-0001-000000000003")),
        "name":         "Air Compressor #2",
        "location":     "Plant B — Utility Room",
        "type":         "Air Compressor",
        "assigned_operator_id": None,
        "health_score": 41.0,
        "risk_level":   "high",
        "rul_hours":    90.0,
        "status":       "critical",
    },
    {
        "machine_id":   str(uuid.UUID("00000000-0000-0000-0001-000000000004")),
        "name":         "Hydraulic Press #5",
        "location":     "Plant B — Bay 2",
        "type":         "Hydraulic Press",
        "assigned_operator_id": None,
        "health_score": 95.1,
        "risk_level":   "low",
        "rul_hours":    2100.0,
        "status":       "normal",
    },
    {
        "machine_id":   str(uuid.UUID("00000000-0000-0000-0001-000000000005")),
        "name":         "Turbine Generator #1",
        "location":     "Power House — Unit 1",
        "type":         "Turbine Generator",
        "assigned_operator_id": None,
        "health_score": 22.8,
        "risk_level":   "critical",
        "rul_hours":    12.0,
        "status":       "critical",
    },
]


def get_db_url() -> str:
    """Read DB URL from environment or .env file."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # Try reading from backend/.env
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"')

    # Default
    return "postgresql+psycopg2://edgetwin:edgetwin@localhost:5432/edgetwin_db"


def seed(db_url: str | None = None) -> None:
    url = db_url or get_db_url()
    print(f"\nConnecting to: {url.split('@')[-1]}")

    engine = create_engine(url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Only seed if the users table is empty (first startup)
        user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
        if user_count > 0:
            print("\nSkipping seed: Users table already populated.")
            print("   (To re-seed, truncate the users table first.)\n")
            return

        _seed_users(session)
        _seed_mechanic_profiles(session)
        _seed_machines(session)
        session.commit()

    _print_credentials()
    print("\nSeeding complete!\n")


def _print_credentials() -> None:
    """Print all demo credentials to the terminal."""
    sep = "-" * 90
    print(f"\n{'='*90}")
    print("  EdgeTwin AI — Demo User Credentials")
    print(f"{'='*90}")
    print(f"  {'#':<3}  {'Role':<25}  {'Email':<30}  {'Password':<20}")
    print(f"  {sep}")
    role_labels = {
        "operator": "Machine Operator",
        "maintenance_manager": "Maintenance Manager",
        "mechanic": "Maintenance Technician",
        "production_manager": "Production Manager",
        "factory_owner": "Factory Owner",
        "admin": "Admin",
    }
    for i, u in enumerate(DEMO_USERS, 1):
        label = role_labels.get(u['role'], u['role'])
        print(f"  {i:<3}  {label:<25}  {u['email']:<30}  {u['password']:<20}")
    print(f"{'='*90}\n")


def _seed_users(session) -> None:
    print("\nSeeding demo users...")

    for u in DEMO_USERS:
        exists = session.execute(
            text("SELECT 1 FROM users WHERE email = :email"),
            {"email": u["email"]},
        ).fetchone()

        if exists:
            print(f"   Skipped  {u['email']}  (already exists)")
            continue

        hashed = _hash(u["password"])
        session.execute(
            text("""
                INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
                VALUES (:user_id, :name, :email, :password_hash, :role, true, :created_at)
            """),
            {
                "user_id":       u["user_id"].replace('-', ''),
                "name":          u["name"],
                "email":         u["email"],
                "password_hash": hashed,
                "role":          u["role"],
                "created_at":    datetime.now(timezone.utc),
            },
        )
        print(f"   Created  {u['email']}  [{u['role']}]")


def _seed_mechanic_profiles(session) -> None:
    print("\nSeeding mechanic profiles...")
    for m in DEMO_MECHANIC_PROFILES:
        exists = session.execute(
            text("SELECT 1 FROM mechanics WHERE mechanic_id = :id"),
            {"id": m["mechanic_id"]},
        ).fetchone()
        if exists:
            print("   Skipped mechanic profile (already exists)")
            continue
        session.execute(
            text("""
                INSERT INTO mechanics (mechanic_id, skill_type, login_status, shift, contact)
                VALUES (:mechanic_id, :skill_type, :login_status, :shift, :contact)
            """),
            {
                "mechanic_id": m["mechanic_id"].replace('-', ''),
                "skill_type": m["skill_type"],
                "login_status": m["login_status"],
                "shift": m["shift"],
                "contact": m["contact"]
            },
        )
        print(f"   Created mechanic profile for {m['mechanic_id']}")


def _seed_machines(session) -> None:
    print("\nSeeding demo machines...")
    for m in DEMO_MACHINES:
        exists = session.execute(
            text("SELECT 1 FROM machines WHERE machine_id = :id"),
            {"id": m["machine_id"]},
        ).fetchone()
        if exists:
            print(f"   Skipped  {m['name']}  (already exists)")
            continue
        machine_params = {**m, "last_updated": datetime.now(timezone.utc)}
        machine_params["machine_id"] = m["machine_id"].replace('-', '')
        if m["assigned_operator_id"]:
            machine_params["assigned_operator_id"] = m["assigned_operator_id"].replace('-', '')
            
        session.execute(
            text("""
                INSERT INTO machines
                  (machine_id, name, location, type, assigned_operator_id,
                   health_score, risk_level, rul_hours, status, last_updated)
                VALUES
                  (:machine_id, :name, :location, :type, :assigned_operator_id,
                   :health_score, :risk_level, :rul_hours, :status, :last_updated)
            """),
            machine_params,
        )
        print(f"   Created  {m['name']}  [risk: {m['risk_level']}]")


if __name__ == "__main__":
    seed()
