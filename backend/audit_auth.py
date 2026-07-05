"""
Full Authentication Audit Script
Checks: DB, users, password hashes, bcrypt, JWT
"""
import sqlite3
import os
import sys

# ─── Step 1: Database check ───────────────────────────────────────────────────
DB_PATH = r"d:\COLLEGE\HACKATHON\Prototype\TATA\backend\edgetwin.db"
print("=" * 70)
print("STEP 1: DATABASE CHECK")
print("=" * 70)
print(f"DB path: {DB_PATH}")
print(f"DB exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"DB size: {os.path.getsize(DB_PATH)} bytes")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

# ─── Step 2: User check ────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 2: USER TABLE CHECK")
print("=" * 70)

if "users" not in tables:
    print("ERROR: 'users' table does not exist!")
    conn.close()
    sys.exit(1)

cur.execute("SELECT user_id, name, email, role, is_active, password_hash FROM users")
users = cur.fetchall()
print(f"Total users: {len(users)}")
print()

for u in users:
    uid, name, email, role, is_active, ph = u
    print(f"  Email    : {email}")
    print(f"  Name     : {name}")
    print(f"  Role     : {role}")
    print(f"  Active   : {is_active}")
    print(f"  Hash     : {ph[:30] if ph else 'NULL'} ...")
    print(f"  Hash len : {len(ph) if ph else 0}")
    print()

conn.close()

# ─── Step 3: bcrypt verification ──────────────────────────────────────────
print("=" * 70)
print("STEP 3: BCRYPT PASSWORD VERIFICATION")
print("=" * 70)

try:
    import bcrypt
    print(f"bcrypt version: {bcrypt.__version__}")
except ImportError:
    print("ERROR: bcrypt not installed!")
    sys.exit(1)

DEMO_PASSWORD = "EdgeTwin@2026"
DEMO_EMAILS = [
    "operator@edgetwin.ai",
    "manager@edgetwin.ai",
    "technician@edgetwin.ai",
    "production@edgetwin.ai",
    "owner@edgetwin.ai",
    "admin@edgetwin.ai",
]

conn2 = sqlite3.connect(DB_PATH)
cur2 = conn2.cursor()

all_ok = True
for email in DEMO_EMAILS:
    cur2.execute("SELECT password_hash FROM users WHERE email=?", (email,))
    row = cur2.fetchone()
    if not row:
        print(f"  MISSING  {email}")
        all_ok = False
        continue
    ph = row[0]
    try:
        ok = bcrypt.checkpw(DEMO_PASSWORD.encode(), ph.encode())
        status = "OK    " if ok else "FAIL  "
        if not ok:
            all_ok = False
    except Exception as e:
        status = f"ERROR ({e})"
        all_ok = False
    print(f"  {status}  {email}  ->  password check: {status.strip()}")

conn2.close()

# ─── Step 4: JWT test ─────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 4: JWT GENERATION AND VALIDATION")
print("=" * 70)

try:
    from jose import jwt
    SECRET = "dev_secret_key_change_in_production_32bytes"
    ALGO   = "HS256"
    import datetime

    payload = {
        "sub": "00000000000000000000000000000001",
        "role": "operator",
        "type": "access",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGO)
    print(f"  Token generated: {token[:40]}...")
    decoded = jwt.decode(token, SECRET, algorithms=[ALGO])
    print(f"  Token decoded  : sub={decoded['sub']}, role={decoded['role']}")
    print("  JWT: OK")
except Exception as e:
    print(f"  JWT ERROR: {e}")
    all_ok = False

# ─── Step 5: Summary ──────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 5: SUMMARY")
print("=" * 70)
if all_ok:
    print("  Backend auth system: ALL CHECKS PASSED")
else:
    print("  Backend auth system: SOME CHECKS FAILED (see above)")

print()
print("DEMO CREDENTIALS (all roles):")
print(f"  Password for all: {DEMO_PASSWORD}")
print()
accounts = [
    ("operator@edgetwin.ai",    "Machine Operator"),
    ("manager@edgetwin.ai",     "Maintenance Manager"),
    ("technician@edgetwin.ai",  "Maintenance Technician"),
    ("production@edgetwin.ai",  "Production Manager"),
    ("owner@edgetwin.ai",       "Factory Owner"),
    ("admin@edgetwin.ai",       "System Admin"),
]
for email, role in accounts:
    print(f"  {role:<25}  {email:<30}  EdgeTwin@2026")
