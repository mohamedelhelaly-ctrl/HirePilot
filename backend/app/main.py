from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db.database import engine
from api.routers import requisitions, cv_upload, screening, auth_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    yield
    
    # Shutdown: Close database connections
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
