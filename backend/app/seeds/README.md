# EdgeTwin AI — Database Seeds

## Files

| File | Purpose |
|---|---|
| `seed_users.py` | Main seeder — called automatically on FastAPI startup (DEBUG=true). Idempotent. |
| `generate_credentials.py` | Standalone script — generates `demo_users.sql` and `demo_credentials.json` |
| `demo_users.sql` | Ready-to-run PostgreSQL SQL (generated) |
| `demo_credentials.json` | Plain-text credentials for dev reference (generated, gitignored) |

## How to Run

### Option 1 — Automatic (FastAPI startup)
Start the backend with `DEBUG=true` (default in `.env`). The seeder runs automatically.

### Option 2 — Manual (when PostgreSQL is running via Docker)
```bash
# Start infrastructure
docker-compose up postgres -d

# Run seeder
cd d:\COLLEGE\HACKATHON\Prototype\TATA
python backend/app/seeds/seed_users.py
```

### Option 3 — Direct SQL (paste into any PostgreSQL client)
```bash
psql -U edgetwin -d edgetwin_db -f backend/app/seeds/demo_users.sql
```

### Option 4 — Regenerate SQL + credentials
```bash
python backend/app/seeds/generate_credentials.py
```
