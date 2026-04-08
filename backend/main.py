"""WEARME FastAPI application factory."""

from __future__ import annotations

import logging
import threading

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.routers import auth_router, avatar_router, user_router

logger = logging.getLogger(__name__)


def _prewarm_smpl() -> None:
    """Load SMPL PKL files into memory cache on a background thread.

    This prevents the first /api/avatar/mesh request from being slow (~1s).
    Runs in a daemon thread so it never blocks server startup.
    """
    try:
        from core.smpl_model import load_smpl
        from core.beta_calibrator import get_calibration
        for gender in ("male", "female"):
            model = load_smpl(gender)
            get_calibration(model, gender)
            logger.info("SMPL model + calibration pre-warmed: %s", gender)
    except Exception:
        logger.exception("SMPL pre-warm failed (non-fatal)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)
    # Pre-load SMPL models in background (non-blocking)
    threading.Thread(target=_prewarm_smpl, daemon=True).start()
    yield


app = FastAPI(
    title="WEARME API",
    description="Virtual clothing try-on backend",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(avatar_router.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}
