from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db.database import engine
from api.routers import requisitions, cv_upload, screening, auth_router
from api.routers.interview import router as interview_router
from scheduler import scheduler
from services.whisper_service import load_whisper, unload_whisper

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logging.getLogger("apscheduler").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # ── Startup ───────────────────────────────────────────────────────────────
    import asyncio
    # Load Whisper in a thread so it doesn't block the event loop
    await asyncio.to_thread(load_whisper)
    logger.info("Whisper model loaded")

    scheduler.start()
    logger.info("Screening scheduler started")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    logger.info("Screening scheduler stopped")
    unload_whisper()
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title="Incorta-HR API",
    description="AI-powered recruitment assistant for Incorta's internal HR team",
    version="1.0.0",
    lifespan=lifespan
)


# Include routers
app.include_router(auth_router.router, prefix="/api", tags=["Authentication"])
app.include_router(requisitions.router, prefix="/api/requisitions", tags=["Requisitions"])
app.include_router(cv_upload.router, prefix="/api/cvs", tags=["CV Upload"])
app.include_router(screening.router, prefix="/api/screening", tags=["Screening"])
app.include_router(interview_router, prefix="/api/interview", tags=["Interview"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Incorta-HR API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "service": "running"
    }