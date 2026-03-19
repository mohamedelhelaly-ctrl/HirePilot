"""Database package initialization."""
import sys
from pathlib import Path

# Ensure backend/app is importable as top-level packages (db, schemas) across runtimes.
APP_ROOT = Path(__file__).resolve().parents[1]
app_root_str = str(APP_ROOT)
if app_root_str not in sys.path:
    sys.path.insert(0, app_root_str)

from .database import Base, engine, AsyncSessionLocal, get_db
from .models import (
    User, Requisition, Candidate, Application, ApplicationDetail,
    ScreeningResult, InterviewSession, TranscriptChunk, StatusHistory,
    WebhookEvent, RefreshToken, UserRole, ApplicationStatus,
    InterviewType, InterviewStatus
)
from . import crud

__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "User",
    "Requisition",
    "Candidate",
    "Application",
    "ApplicationDetail",
    "ScreeningResult",
    "InterviewSession",
    "TranscriptChunk",
    "StatusHistory",
    "WebhookEvent",
    "RefreshToken",
    "UserRole",
    "ApplicationStatus",
    "InterviewType",
    "InterviewStatus",
    "crud",
]
