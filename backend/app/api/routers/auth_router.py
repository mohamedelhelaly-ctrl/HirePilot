"""
Authentication API router.
Handles email/password login, google oauth, token refresh, current user endpoints, and logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User
from schemas import LoginRequest, Token, User as UserSchema, GoogleLoginRequest, TokenRefreshRequest, LogoutRequest, LogoutResponse, AdminUserCreate
from services.auth_service import (
    google_login,
    refresh_access_token,
    logout,
    create_admin_user,
    setup_initial_admin
)
from dependencies import get_current_user, require_hr_manager


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


@router.post(
    "/admin/users",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create New User (Admin Only)",
    description="Create a new employee account for pre-registration (HR managers only)"
)
async def create_user_admin(
    request: AdminUserCreate,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Create a new employee account for pre-registration (admin endpoint).
    
    This endpoint allows HR managers to pre-register employees in the system.
    Employees created here will authenticate using Google OAuth via email matching.
    No password is required at creation time.
    
    Authentication:
        Required - HR Manager role only
        Include access token in Authorization header:
        Authorization: Bearer <access_token>
    
    Request body:
    - email: Employee email address (must be unique)
    - full_name: Employee's full name
    - role: Employee role (hr_manager or hiring_manager)
    
    Response:
    - id: Newly created user ID
    - email: User email address
    - full_name: User's full name
    - role: User role
    - is_active: Account active status (true)
    - created_at: Account creation timestamp
    - updated_at: Last update timestamp
    
    Authentication Flow:
    1. Employee is pre-registered with email and role
    2. No password is set (hashed_password = "")
    3. Employee logs in with Google OAuth
    4. System finds employee by email and logs them in
    5. Refresh tokens are generated and stored
    
    Raises:
        HTTPException(400): User with email already exists
        HTTPException(401): Missing or invalid access token
        HTTPException(403): User is not an HR manager
        HTTPException(500): Database error
    
    Example:
        POST /api/auth/admin/users
        Authorization: Bearer <access_token>
        
        {
            "email": "john.doe@company.com",
            "full_name": "John Doe",
            "role": "hiring_manager"
        }
        
        Response (201):
        {
            "id": 42,
            "email": "john.doe@company.com",
            "full_name": "John Doe",
            "role": "hiring_manager",
            "is_active": true,
            "created_at": "2026-04-13T10:30:00",
            "updated_at": "2026-04-13T10:30:00"
        }
    """
    return await create_admin_user(
        db=db,
        email=request.email,
        full_name=request.full_name,
        role=request.role
    )


@router.post(
    "/setup",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Initial System Setup",
    description="One-time endpoint to create the first admin user (HR manager)"
)
async def setup_system(
    request: AdminUserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    One-time endpoint to initialize the system with the first admin user.
    
    This endpoint creates the very first HR_MANAGER user in the system during setup.
    It can ONLY be called when NO HR_MANAGER users exist yet.
    After setup is complete, it will always return 403 Forbidden.
    
    This is an UNAUTHENTICATED endpoint (no login required).
    It is only available during bootstrap - once an admin exists, it's locked.
    
    Request body:
    - email: Admin email address
    - full_name: Admin full name
    - role: Must be "hr_manager"
    
    Response:
    - id: Newly created user ID
    - email: User email address
    - full_name: User's full name
    - role: Always "hr_manager"
    - is_active: Account active status (true)
    - created_at: Account creation timestamp
    - updated_at: Last update timestamp
    
    Authentication Flow After Setup:
    1. Admin logs in with Google OAuth using their email
    2. System creates tokens
    3. Admin can now use /api/auth/admin/users to create other users
    
    System States:
    
    1. Fresh Installation (Before First Setup):
       - POST /api/auth/setup → 201 Created (success, first admin created)
       - POST /api/auth/setup again → 403 Forbidden (setup already complete)
    
    2. After Setup Complete:
       - POST /api/auth/setup → 403 Forbidden (always, use /admin/users instead)
    
    Errors:
    - 400: User with email already exists
    - 403: System already initialized (admin exists)
    - 422: Role must be "hr_manager"
    - 500: Database error
    
    Security Notes:
    - This endpoint is public but self-locks after first use
    - No authentication required (but only works once)
    - Subsequent user creation requires admin authentication
    - Use environment variables to set the initial admin in production
    
    Example - Fresh Installation:
        POST /api/auth/setup
        (No authorization header needed)
        
        {
            "email": "admin@company.com",
            "full_name": "System Administrator",
            "role": "hr_manager"
        }
        
        Response (201):
        {
            "id": 1,
            "email": "admin@company.com",
            "full_name": "System Administrator",
            "role": "hr_manager",
            "is_active": true,
            "created_at": "2026-04-13T10:30:00",
            "updated_at": "2026-04-13T10:30:00"
        }
    
    Example - Subsequent Call (Already Initialized):
        POST /api/auth/setup
        
        Response (403):
        {
            "detail": "System is already initialized. An HR_MANAGER user already exists. 
                       Use /api/auth/admin/users to create additional users."
        }
    """
    return await setup_initial_admin(
        db=db,
        email=request.email,
        full_name=request.full_name,
        role=request.role
    )
