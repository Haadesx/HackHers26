"""
FastAPI application entrypoint.
"""
from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.repo import init_db, _init_redis
from app.api import payments, liveness, audit

settings = get_settings()
setup_logging(settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.VERSION)
    await init_db()
    await _init_redis()
    logger.info(
        "Services: gemini=%s elevenlabs=%s solana=%s fiserv=%s",
        "live" if settings.gemini_configured else "stub",
        "live" if settings.elevenlabs_configured else "stub",
        "live" if settings.solana_configured else "stub",
        "live" if settings.fiserv_configured else "simulator",
    )
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Deepfake + Presage biometric payment gate — risk-based step-up verification.",
    lifespan=lifespan,
)

# CORS — allow localhost frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(payments.router, tags=["Payments"])
app.include_router(liveness.router, tags=["Liveness"])
app.include_router(audit.router, tags=["Audit"])


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "services": {
            "gemini": "live" if settings.gemini_configured else "stub",
            "elevenlabs": "live" if settings.elevenlabs_configured else "stub",
            "solana": "live" if settings.solana_configured else "stub",
            "bank_gateway": "fiserv" if settings.fiserv_configured else "simulator",
        },
    }
