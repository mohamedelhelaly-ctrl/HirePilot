from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from stores.llm.whisper_service import load_whisper
from models.database import get_db, engine
from routers import auth_router, requisition_router, candidate_router, maingraph_router, interview_router
from stores.vectordb.load_model import download_model
from stores.vectordb.embedding_model import get_embedding_model
from stores.llm.whisper_service import load_whisper
# from api.routers import requisitions, cv_upload, screening, auth_router
# from api.routers.interview import router as interview_router
# from api.routers.rag_router import router as rag_router
# from scheduler import scheduler
# from services.whisper_service import load_whisper, unload_whisper

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

    # embedding model
    download_model()
    app.embedding_model = get_embedding_model()

    # Load Whisper
    await asyncio.to_thread(load_whisper)
    logger.info("Whisper model loaded")

    # Initialize database
    # app.db = get_db()
    

    # scheduler.start()
    # logger.info("Screening scheduler started")

    yield

    # # ── Shutdown ──────────────────────────────────────────────────────────────
    # scheduler.shutdown(wait=False)
    # logger.info("Screening scheduler stopped")
    # unload_whisper()
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title="Incorta-HR API",
    description="AI-powered recruitment assistant for Incorta's internal HR team",
    version="1.0.0",
    lifespan=lifespan,
    debug=True
)

# Allow requests from localhost for testing and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api", tags=["authentication"])
app.include_router(requisition_router, prefix="/api", tags=["requisitions"])
app.include_router(candidate_router, prefix="/api/candidates", tags=["candidates"])
app.include_router(maingraph_router, prefix="/api", tags=["main orchestrator graph"])
app.include_router(interview_router, prefix="/api", tags=["interviews"])


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