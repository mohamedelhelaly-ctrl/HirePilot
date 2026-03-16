"""
Authentication API router.
Handles email/password login, google oauth, token refresh, current user endpoints, and logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User
from schemas import LoginRequest, Token, User as UserSchema, GoogleLoginRequest, TokenRefreshRequest, LogoutRequest, LogoutResponse
from services.auth_service import (
    email_login,
    google_login,
    refresh_access_token,
    logout
)
from dependencies import get_current_user


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired credentials"},
        403: {"description": "Forbidden - User not found or not authorized"},
    }
)


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Email/Password Login",
    description="Authenticate with email and password credentials"
)
async def login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate user with email and password.
    
    This endpoint handles traditional email/password authentication flow:
    
    1. Validates email and password credentials
    2. Generates JWT access token (30 minute expiration)
    3. Generates refresh token (7 day expiration)
    4. Stores hashed refresh token in database
    
    Request body:
    - email: User email address
    - password: User password
    
    Response:
    - access_token: JWT token for authenticating API requests
    - refresh_token: Token for obtaining new access tokens
    - token_type: Always "bearer"
    
    Raises:
        HTTPException(401): Invalid email or password
        HTTPException(500): Database error
    """
    return await email_login(db, login_request)


@router.post(
    "/google",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth Login",
    description="Authenticate with Google OAuth ID token"
)
async def google_auth(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate user with Google OAuth ID token.
    
    This endpoint handles Google OAuth authentication:
    
    1. Verifies Google ID token signature and claims
    2. Extracts user email and profile information
    3. Finds existing user in database (pre-registration required)
    4. Generates JWT access token (30 minute expiration)
    5. Generates refresh token (7 day expiration)
    6. Stores hashed refresh token in database
    
    Request body:
    - id_token: Google ID token from frontend
    
    Response:
    - access_token: JWT token for authenticating API requests
    - refresh_token: Token for obtaining new access tokens
    - token_type: Always "bearer"
    
    Important:
        Users must be pre-registered in the database.
        This endpoint does NOT auto-create new users.
    
    Raises:
        HTTPException(400): Invalid or malformed ID token
        HTTPException(403): User not found in database
        HTTPException(500): Database error
    """
    return await google_login(db, request.id_token)


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Get a new access token using refresh token"
)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Generate new access token using refresh token.
    
    This endpoint allows clients to obtain a new access token
    without requiring credentials re-entry:
    
    1. Validates refresh token signature and claims
    2. Verifies refresh token exists in database (not revoked)
    3. Loads user and verifies user is active
    4. Generates new access token (30 minute expiration)
    5. Returns the same refresh token (can be reused)
    
    Request body:
    - refresh_token: Previously obtained refresh token
    
    Response:
    - access_token: New JWT token for authenticating API requests
    - refresh_token: Same refresh token (unchanged)
    - token_type: Always "bearer"
    
    Raises:
        HTTPException(401): Invalid, expired, or revoked refresh token
        HTTPException(403): User is inactive
        HTTPException(500): Database error
    """
    return await refresh_access_token(db, request.refresh_token)


@router.get(
    "/me",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get profile of currently authenticated user"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current authenticated user's profile.
    
    This endpoint returns the profile of the user
    whose access token was used in the request.
    
    Authentication:
        Required - Include access token in Authorization header:
        Authorization: Bearer <access_token>
    
    Response:
    - id: User ID
    - email: User email address
    - full_name: User's full name
    - role: User role (hr_manager or hiring_manager)
    - is_active: Whether user account is active
    - created_at: Account creation timestamp
    - updated_at: Last update timestamp
    
    Raises:
        HTTPException(401): Missing or invalid access token
        HTTPException(403): User is inactive
        HTTPException(500): Database error
    """
    return current_user


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout User",
    description="Logout and revoke refresh token(s)"
)
async def logout_user(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LogoutResponse:
    """
    Logout user by revoking refresh token(s).
    
    This endpoint revokes refresh tokens to invalidate them:
    
    1. If specific refresh_token is provided:
       - Revokes only that refresh token
       - User can still use other refresh tokens
    
    2. If refresh_token is not provided:
       - Revokes ALL refresh tokens for the user
       - Requires full re-authentication to obtain new tokens
    
    Authentication:
        Required - Include access token in Authorization header:
        Authorization: Bearer <access_token>
    
    Request body (optional):
    - refresh_token: Optional refresh token to revoke
                    If omitted, all tokens for the user are revoked
    
    Response:
    - message: Status message indicating logout success
    
    After logout:
    - Access tokens can no longer be refreshed
    - Refresh tokens are invalid
    - User must login again to obtain new tokens
    
    Raises:
        HTTPException(401): Missing or invalid access token
        HTTPException(403): User is inactive
        HTTPException(500): Database error
    """
    result = await logout(
        db=db,
        user_id=current_user.id,
        refresh_token=request.refresh_token
    )
    return LogoutResponse(message=result["message"])
