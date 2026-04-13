"""
Authentication Service module.
Handles login, token generation, and credential verification.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_user_by_email,
    get_user_by_id,
    create_refresh_token as crud_create_refresh_token,
    get_refresh_token_by_hash,
    check_admin_exists,
)
from db.models import User, UserRole
from schemas import LoginRequest, Token
from security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    GOOGLE_CLIENT_ID,
)
from db.crud import delete_refresh_token, delete_user_refresh_tokens


# --- Constants ---
REFRESH_TOKEN_EXPIRE_DAYS = 7


# --- Helper Functions ---

def build_user_claims(user: User) -> Dict[str, Any]:
    """Build JWT claims from user object."""
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
    }


def ensure_user_exists(user: Optional[User]) -> User:
    """Ensure the user exists."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def ensure_user_active(user: User) -> None:
    """Ensure user account is active."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )


def verify_google_token(id_token_str: str) -> Dict[str, Any]:
    """Verify Google OAuth ID token and return payload."""
    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID token: {str(e)}"
        )


async def generate_auth_tokens(db: AsyncSession, user: User) -> Token:
    """
    Generate access and refresh tokens for a user and store
    hashed refresh token in database.
    """
    access_token = create_access_token(data=build_user_claims(user))
    refresh_token = create_refresh_token(user_id=user.id)
    token_hash = hash_token(refresh_token)

    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    await crud_create_refresh_token(
        db=db,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# --- Authentication Logic ---

async def email_login(db: AsyncSession, login_request: LoginRequest) -> Token:
    """Authenticate user with email and password."""
    user = await get_user_by_email(db, login_request.email)

    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ensure_user_active(user)
    return await generate_auth_tokens(db, user)


async def google_login(db: AsyncSession, id_token_str: str) -> Token:
    """Authenticate user using Google OAuth ID token."""
    payload = verify_google_token(id_token_str)
    email = payload.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in ID token"
        )

    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found. Please register before logging in."
        )

    ensure_user_active(user)
    return await generate_auth_tokens(db, user)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Token:
    """Generate new access token using a valid refresh token."""
    payload = decode_refresh_token(refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    token_hash = hash_token(refresh_token)
    stored_token = await get_refresh_token_by_hash(db, token_hash)

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = ensure_user_exists(await get_user_by_id(db, user_id))
    ensure_user_active(user)

    new_access_token = create_access_token(data=build_user_claims(user))

    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


async def get_current_user(db: AsyncSession, user_id: int) -> User:
    """Retrieve current user from database."""
    user = ensure_user_exists(await get_user_by_id(db, user_id))
    ensure_user_active(user)
    return user


async def logout(db: AsyncSession, user_id: int, refresh_token: Optional[str] = None) -> Dict[str, str]:
    """
    Logout user by revoking refresh token(s).
    
    Args:
        db: Database session
        user_id: ID of user logging out
        refresh_token: Optional specific refresh token to revoke. 
                      If None, revokes all refresh tokens for the user.
    
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If user not found or token revocation fails
    """
    
    user = ensure_user_exists(await get_user_by_id(db, user_id))
    
    if refresh_token:
        # Revoke specific refresh token
        token_hash = hash_token(refresh_token)
        await delete_refresh_token(db, token_hash)
        return {"message": "Logged out successfully"}
    else:
        # Revoke all refresh tokens for the user
        revoked_count = await delete_user_refresh_tokens(db, user_id)
        return {
            "message": f"Logged out successfully. Revoked {revoked_count} token(s)."
        }


# --- Admin User Management ---

async def create_admin_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    role: UserRole
) -> User:
    """
    Create a new user for pre-registration (admin endpoint).
    
    Used to pre-register employees before they login with Google OAuth.
    The user will authenticate via email matching with Google OAuth.
    
    Steps:
    1. Check if user with email already exists
    2. If exists, raise 400 BadRequest
    3. Create user with no password (Google OAuth only)
    4. Save to database
    5. Return created user
    
    Args:
        db: Database session
        email: User email address (unique)
        full_name: User's full name
        role: User role (HR_MANAGER or HIRING_MANAGER)
    
    Returns:
        Created User object
        
    Raises:
        HTTPException(400): If user with email already exists
        HTTPException(500): Database error
    """
    
    # Step 1: Check if user with email already exists
    existing_user = await get_user_by_email(db, email)
    
    # Step 2: If exists, raise 400 BadRequest
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email}' already exists"
        )
    
    # Step 3: Create user with no password (Google OAuth only)
    # hashed_password is set to empty string since it's nullable=False in DB
    # but will not be used for OAuth-only users
    new_user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password="",  # No password for OAuth-only users
        is_active=True
    )
    
    # Step 4: Save to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Step 5: Return created user
    return new_user


# --- Initial Setup (One-time endpoint) ---

async def setup_initial_admin(
    db: AsyncSession,
    email: str,
    full_name: str,
    role: UserRole
) -> User:
    """
    One-time endpoint to create the first admin user (HR_MANAGER).
    
    This is a bootstrap function for initial system setup.
    Can only be used when NO HR_MANAGER users exist in the database.
    
    Steps:
    1. Check if any HR_MANAGER already exists
    2. If exists, raise 403 Forbidden (setup already complete)
    3. Check if email already exists
    4. If exists, raise 400 BadRequest
    5. Enforce role must be HR_MANAGER (safety)
    6. Create user with no password (Google OAuth only)
    7. Save to database
    8. Return created user
    
    Args:
        db: Database session
        email: Admin email address
        full_name: Admin full name
        role: User role (must be HR_MANAGER)
    
    Returns:
        Created User object
        
    Raises:
        HTTPException(400): If email already exists
        HTTPException(403): If admin already exists (setup already complete)
        HTTPException(422): If role is not HR_MANAGER
        HTTPException(500): Database error
    """
    
    # Step 1: Check if any HR_MANAGER already exists
    admin_exists = await check_admin_exists(db)
    
    # Step 2: If exists, raise 403 Forbidden (setup already complete)
    if admin_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System is already initialized. An HR_MANAGER user already exists. "
                   "Use /api/auth/admin/users to create additional users."
        )
    
    # Step 3: Enforce role must be HR_MANAGER (safety check)
    if role != UserRole.HR_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Initial admin user must have role: hr_manager"
        )
    
    # Step 4: Check if email already exists
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email}' already exists"
        )
    
    # Step 5: Create user with no password (Google OAuth only)
    new_admin = User(
        email=email,
        full_name=full_name,
        role=UserRole.HR_MANAGER,
        hashed_password="",  # No password for OAuth-only users
        is_active=True
    )
    
    # Step 6: Save to database
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    
    # Step 7: Return created user
    return new_admin