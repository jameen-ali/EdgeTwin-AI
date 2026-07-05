import json
from datetime import datetime, timezone
import bcrypt


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


DEMO_USERS = [
    {
        "user_id":     "00000000-0000-0000-0000-000000000001",
        "name":        "Alex Morgan",
        "email":       "operator@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "operator",
        "role_label":  "Machine Operator",
        "dashboard":   "/operator",
    },
    {
        "user_id":     "00000000-0000-0000-0000-000000000002",
        "name":        "Sarah Chen",
        "email":       "manager@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "maintenance_manager",
        "role_label":  "Maintenance Manager",
        "dashboard":   "/maintenance",
    },
    {
        "user_id":     "00000000-0000-0000-0000-000000000003",
        "name":        "Raj Patel",
        "email":       "technician@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "mechanic",
        "role_label":  "Maintenance Technician",
        "dashboard":   "/mechanic",
    },
    {
        "user_id":     "00000000-0000-0000-0000-000000000004",
        "name":        "Diana Osei",
        "email":       "production@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "production_manager",
        "role_label":  "Production Manager",
        "dashboard":   "/production",
    },
    {
        "user_id":     "00000000-0000-0000-0000-000000000005",
        "name":        "Marcus Liu",
        "email":       "owner@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "factory_owner",
        "role_label":  "Factory Owner",
        "dashboard":   "/owner",
    },
    {
        "user_id":     "00000000-0000-0000-0000-000000000006",
        "name":        "System Admin",
        "email":       "admin@edgetwin.ai",
        "password":    "EdgeTwin@2026",
        "role":        "admin",
        "role_label":  "System Admin",
        "dashboard":   "/admin",
    },
]

DEMO_MACHINES = [
    {
        "machine_id":             "00000000-0000-0000-0001-000000000001",
        "name":                   "CNC Mill #1",
        "location":               "Plant A — Bay 1",
        "type":                   "CNC Milling Machine",
        "assigned_operator_id":   "00000000-0000-0000-0000-000000000001",
        "health_score":           87.5,
        "risk_level":             "low",
        "rul_hours":              1240.0,
        "status":                 "normal",
    },
    {
        "machine_id":             "00000000-0000-0000-0001-000000000002",
        "name":                   "Conveyor Belt #3",
        "location":               "Plant A — Bay 3",
        "type":                   "Conveyor System",
        "assigned_operator_id":   "00000000-0000-0000-0000-000000000001",
        "health_score":           63.2,
        "risk_level":             "medium",
        "rul_hours":              480.0,
        "status":                 "warning",
    },
    {
        "machine_id":             "00000000-0000-0000-0001-000000000003",
        "name":                   "Air Compressor #2",
        "location":               "Plant B — Utility Room",
        "type":                   "Air Compressor",
        "assigned_operator_id":   None,
        "health_score":           41.0,
        "risk_level":             "high",
        "rul_hours":              90.0,
        "status":                 "critical",
    },
    {
        "machine_id":             "00000000-0000-0000-0001-000000000004",
        "name":                   "Hydraulic Press #5",
        "location":               "Plant B — Bay 2",
        "type":                   "Hydraulic Press",
        "assigned_operator_id":   None,
        "health_score":           95.1,
        "risk_level":             "low",
        "rul_hours":              2100.0,
        "status":                 "normal",
    },
    {
        "machine_id":             "00000000-0000-0000-0001-000000000005",
        "name":                   "Turbine Generator #1",
        "location":               "Power House — Unit 1",
        "type":                   "Turbine Generator",
        "assigned_operator_id":   None,
        "health_score":           22.8,
        "risk_level":             "critical",
        "rul_hours":              12.0,
        "status":                 "critical",
    },
]


def generate() -> dict:
    """Hash all passwords and return enriched user records."""
    result = []
    for u in DEMO_USERS:
        record = dict(u)
        record["password_hash"] = _hash(u["password"])
        result.append(record)
    return result


def print_table(users: list[dict]) -> None:
    sep = "─" * 90
    print(f"\n{'═'*90}")
    print("  EdgeTwin AI — Demo User Credentials")
    print(f"{'═'*90}")
    print(f"  {'#':<3}  {'Role':<25}  {'Email':<30}  {'Password':<25}")
    print(f"  {sep}")
    for i, u in enumerate(users, 1):
        print(f"  {i:<3}  {u['role_label']:<25}  {u['email']:<30}  {u['password']:<25}")
    print(f"{'═'*90}\n")


def write_sql(users: list[dict], output_path: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "-- EdgeTwin AI — Demo User Seed SQL",
        f"-- Generated: {now}",
        "-- Run this against your PostgreSQL edgetwin_db database.",
        "",
        "BEGIN;",
        "",
        "-- ── Users ─────────────────────────────────────────────────────────",
    ]

    for u in users:
        lines.append(
            f"INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)\n"
            f"VALUES ('{u['user_id']}', '{u['name']}', '{u['email']}',\n"
            f"        '{u['password_hash']}',\n"
            f"        '{u['role']}', true, NOW())\n"
            f"ON CONFLICT (email) DO NOTHING;\n"
        )

    # Mechanic profile
    lines += [
        "",
        "-- ── Mechanic Profile ──────────────────────────────────────────────",
        "INSERT INTO mechanics (mechanic_id, skill_type, login_status, shift, contact)",
        "VALUES ('00000000-0000-0000-0000-000000000003',",
        "        'Electrical & Mechanical', 'available', 'Morning', '+1-555-0103')",
        "ON CONFLICT (mechanic_id) DO NOTHING;",
        "",
        "-- ── Demo Machines ──────────────────────────────────────────────────",
    ]

    for m in DEMO_MACHINES:
        op = f"'{m['assigned_operator_id']}'" if m["assigned_operator_id"] else "NULL"
        lines.append(
            f"INSERT INTO machines\n"
            f"  (machine_id, name, location, type, assigned_operator_id,\n"
            f"   health_score, risk_level, rul_hours, status, last_updated)\n"
            f"VALUES\n"
            f"  ('{m['machine_id']}', '{m['name']}', '{m['location']}', '{m['type']}', {op},\n"
            f"   {m['health_score']}, '{m['risk_level']}', {m['rul_hours']}, '{m['status']}', NOW())\n"
            f"ON CONFLICT (machine_id) DO NOTHING;\n"
        )

    lines += ["", "COMMIT;", ""]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📄  SQL written → {output_path}")


def write_json(users: list[dict], output_path: str) -> None:
    """Write a credentials JSON file (useful for CI/test fixtures)."""
    export = [
        {
            "name":      u["name"],
            "email":     u["email"],
            "password":  u["password"],
            "role":      u["role"],
            "dashboard": u["dashboard"],
        }
        for u in users
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)
    print(f"📄  JSON written → {output_path}")


if __name__ == "__main__":
    import os
    output_dir = os.path.dirname(__file__)

    users = generate()
    print_table(DEMO_USERS)  # Print plain-text passwords (not hashes)

    write_sql(users, os.path.join(output_dir, "demo_users.sql"))
    write_json(DEMO_USERS, os.path.join(output_dir, "demo_credentials.json"))
    print("\n💡  To load into PostgreSQL:")
    print("   psql -U edgetwin -d edgetwin_db -f backend/app/seeds/demo_users.sql\n")
