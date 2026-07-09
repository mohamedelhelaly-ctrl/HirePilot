"""
Google OAuth Service module.
Handles authorization code exchange, token refresh, and credential management
for Google Calendar integration.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from helpers.config import get_settings
from models.crud.google_oauth_crud import (
    get_google_oauth_credential,
    update_google_oauth_credential,
)
from controllers.services.security import decrypt_token

# ============================================================================
# Configuration
# ============================================================================

settings = get_settings()
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ============================================================================
# Authorization Code Exchange
# ============================================================================

async def exchange_authorization_code_for_tokens(auth_code: str) -> Dict[str, Any]:
    """
    Exchange Google authorization code for access and refresh tokens.
    
    This implements the Authorization Code Flow server-side token exchange.
    The frontend sends the authorization code to the backend, which exchanges
    it for Google tokens using the client secret (never exposed to frontend).
    
    Args:
        auth_code: The authorization code from Google OAuth consent screen
        
    Returns:
        Dictionary with:
            - access_token: Bearer token for Google API calls
            - refresh_token: Token to refresh access token after expiry
            - expires_in: Seconds until access token expires
            - token_type: Always "Bearer"
            
    Raises:
        HTTPException: If code exchange fails
    """
    payload = {
        "code": auth_code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )


# ============================================================================
# Token Refresh
# ============================================================================

async def refresh_google_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Use a refresh token to obtain a new access token.
    
    Google access tokens expire after ~1 hour. This function uses the refresh
    token to get a new access token without requiring user to re-authenticate.
    
    Args:
        refresh_token: The plaintext refresh token
        
    Returns:
        Dictionary with:
            - access_token: New bearer token
            - expires_in: Seconds until expiry
            
    Raises:
        HTTPException: If refresh fails
    """
    payload = {
        "refresh_token": refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to refresh Google access token: {str(e)}"
        )


async def get_valid_google_access_token(db: AsyncSession, user_id: int) -> str:
    """
    Get a valid Google access token, refreshing if necessary.
    
    Checks if the stored access token has expired. If it has, uses the refresh
    token to obtain a new one and updates the database.
    
    Args:
        db: Database session
        user_id: User ID to fetch token for
        
    Returns:
        Valid plaintext access token
        
    Raises:
        HTTPException: If user has no Google credentials or refresh fails
    """
    credential = await get_google_oauth_credential(db, user_id)
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User has not connected Google account"
        )
    
    # Check if token is expired (with 5 minute buffer)
    buffer = timedelta(minutes=5)
    if credential.token_expiry <= datetime.now(timezone.utc) + buffer:
        # Token expired, refresh it
        refresh_token_plain = decrypt_token(credential.refresh_token)
        token_response = await refresh_google_access_token(refresh_token_plain)
        
        # Update database with new token
        new_access_token = token_response.get("access_token")
        expires_in = token_response.get("expires_in", 3600)
        new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        await update_google_oauth_credential(
            db=db,
            user_id=user_id,
            access_token=new_access_token,
            refresh_token=refresh_token_plain,  # Refresh token usually doesn't change
            token_expiry=new_expiry
        )
        
        return new_access_token
    else:
        # Token still valid, return it
        return decrypt_token(credential.access_token)


# ============================================================================
# User Info Verification
# ============================================================================

async def verify_google_access_token(access_token: str) -> Dict[str, Any]:
    """
    Verify access token and get user profile info from Google.
    
    Args:
        access_token: Google access token to verify
        
    Returns:
        Dictionary with user profile info (id, email, name, picture, etc.)
        
    Raises:
        HTTPException: If token is invalid or API call fails
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to verify Google access token: {str(e)}"
        )


# ============================================================================
# Credential Storage
# ============================================================================
# Credential storage is handled by google_oauth_crud module
