from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.router import api_router
from app.websocket.events import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev — use Alembic in prod)
    Base.metadata.create_all(bind=engine)

    # Auto-seed the full database if it is empty
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    
    try:
        from scripts.seed_full_db import seed_db
        seed_db()
    except Exception as exc:
        import logging
        logging.getLogger("edgetwin").warning(f"Full seeder failed: {exc}")

    # Start IoT Simulator in the background so telemetry flows automatically
    import threading
    import time
    def delayed_simulator():
        time.sleep(5) # Wait for FastAPI to start accepting requests
        try:
            # Tell simulator to use localhost since it's running in the same container
            os.environ["VITE_API_URL"] = "http://localhost:8000"
            from scripts.sensor_simulator import run_simulation
            run_simulation()
        except Exception as e:
            import logging
            logging.getLogger("edgetwin").error(f"Simulator crashed: {e}")

    threading.Thread(target=delayed_simulator, daemon=True).start()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Predictive Maintenance Platform — Industry 4.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Router ───────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ─── WebSocket Router ─────────────────────────────────────────────────────────
app.include_router(ws_router)



@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
