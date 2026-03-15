"""
Authentication Service module.
Handles login, token generation, and credential verification.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status

from app.db.crud import (
    get_user_by_email,
    get_user_by_id,
    create_refresh_token as crud_create_refresh_token,
    get_refresh_token_by_hash,
    delete_refresh_token
)
from app.db.models import User, UserRole
from app.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    GOOGLE_CLIENT_ID
)
from app.schemas import LoginRequest, Token


# ============================================================================
# Email/Password Login
# ============================================================================

async def email_login(db: AsyncSession, login_request: LoginRequest) -> Token:
    """
    Authenticate user with email and password.
    
    Steps:
    1. Fetch user by email
    2. Verify password matches
    3. Generate JWT access token with user claims
    4. Generate refresh token and store hashed version in database
    5. Return Token schema
    
    Args:
        db: Database session
        login_request: LoginRequest containing email and password
        
    Returns:
        Token schema with access_token, refresh_token, and token_type
        
    Raises:
        HTTPException(401): If email/password are invalid
    """
    # Step 1: Fetch user by email
    user = await get_user_by_email(db, login_request.email)
    
    # Step 2: Verify user exists and password is correct
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3: Generate access token with user claims
    access_token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    }
    access_token = create_access_token(data=access_token_data)
    
    # Step 4: Generate refresh token and store hashed version in database
    refresh_token = create_refresh_token(user_id=user.id)
    token_hash = hash_token(refresh_token)
    
    # Store in database with 7-day expiration
    expires_at = datetime.utcnow() + timedelta(days=7)
    await crud_create_refresh_token(db, user.id, token_hash, expires_at)
    
    # Step 5: Return token response
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# ============================================================================
# Google OAuth Login
# ============================================================================

async def google_login(db: AsyncSession, id_token_str: str) -> Token:
    """
    Authenticate user with Google OAuth ID token.
    
    Steps:
    1. Verify Google ID token signature and claims
    2. Extract email, name, and Google user ID
    3. Find existing user by email
    4. If user not found, return 403 Forbidden (pre-registration required)
    5. Generate access token and refresh token
    6. Store hashed refresh token in database
    7. Return Token schema
    
    Args:
        db: Database session
        id_token_str: Google ID token string
        
    Returns:
        Token schema with access_token, refresh_token, and token_type
        
    Raises:
        HTTPException(400): If ID token is invalid
        HTTPException(403): If user does not exist in database
    """
    # Step 1: Verify Google ID token
    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID token: {str(e)}"
        )
    
    # Step 2: Extract user information from token payload
    email = payload.get('email')
    name = payload.get('name')
    google_user_id = payload.get('sub')
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in ID token"
        )
    
    # Step 3: Find existing user by email
    user = await get_user_by_email(db, email)
    
    # Step 4: If user not found, require pre-registration
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found. Please register before logging in."
        )
    
    # Step 5: Generate access token with user claims
    access_token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    }
    access_token = create_access_token(data=access_token_data)
    
    # Step 6: Generate refresh token and store hashed version in database
    refresh_token = create_refresh_token(user_id=user.id)
    token_hash = hash_token(refresh_token)
    
    # Store in database with 7-day expiration
    expires_at = datetime.utcnow() + timedelta(days=7)
    await crud_create_refresh_token(db, user.id, token_hash, expires_at)
    
    # Step 7: Return token response
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# ============================================================================
# Token Refresh
# ============================================================================

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Token:
    """
    Generate new access token using a valid refresh token.
    
    Steps:
    1. Decode and validate refresh token
    2. Verify refresh token exists in database
    3. Load user and verify user is active
    4. Generate new access token with user claims
    5. Return Token schema
    
    Args:
        db: Database session
        refresh_token: JWT refresh token string
        
    Returns:
        Token schema with new access_token, refresh_token, and token_type
        
    Raises:
        HTTPException(401): If refresh token is invalid or expired
        HTTPException(403): If user is inactive
    """
    # Step 1: Decode and validate refresh token
    payload = decode_refresh_token(refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    
    # Step 2: Verify refresh token exists in database (check hash)
    token_hash = hash_token(refresh_token)
    stored_token = await get_refresh_token_by_hash(db, token_hash)
    
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3: Load user and verify user is active
    user = await get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    # Step 4: Generate new access token with user claims
    access_token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    }
    new_access_token = create_access_token(data=access_token_data)
    
    # Step 5: Return token response (reuse refresh token or generate new one)
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# ============================================================================
# Get Current User
# ============================================================================

async def get_current_user(db: AsyncSession, user_id: int) -> User:
    """
    Retrieve current user from database.
    
    Steps:
    1. Load user by ID
    2. Verify user exists and is active
    
    Args:
        db: Database session
        user_id: User ID from JWT token
        
    Returns:
        User model instance
        
    Raises:
        HTTPException(401): If user not found or inactive
    """
    # Step 1: Load user by ID
    user = await get_user_by_id(db, user_id)
    
    # Step 2: Verify user exists and is active
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    return user
