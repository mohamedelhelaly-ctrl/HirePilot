from pydantic import BaseModel
from typing import Any

# Request/Response Schemas

class GoogleLoginRequest(BaseModel):
    """Google OAuth ID token login request."""
    id_token: str


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str

class LogoutRequest(BaseModel):
    """Request model for logout endpoint."""
    refresh_token: str | None = None


class LogoutResponse(BaseModel):
    """Response model for logout endpoint."""
    message: str


# Batch screening trigger
class TriggerScreeningRequest(BaseModel):
    requisition_id: int
    force: bool = False  # Bypass counter threshold check


# WebSocket message schemas
class WSMessage(BaseModel):
    type: str  # "transcript", "followup_question", "error", "update"
    data: Any