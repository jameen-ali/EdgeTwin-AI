from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev — use Alembic in prod)
    Base.metadata.create_all(bind=engine)

    # Seed demo data on first startup (idempotent — safe to run every time)
    if settings.DEBUG:
        try:
            from app.seeds.seed_users import seed
            seed()
        except Exception as exc:
            # Never crash startup due to seed failure
            import logging
            logging.getLogger("edgetwin").warning(f"Seeder skipped: {exc}")

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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Router ───────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ─── WebSocket Router ─────────────────────────────────────────────────────────
from app.websocket.events import ws_router
app.include_router(ws_router)



@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
