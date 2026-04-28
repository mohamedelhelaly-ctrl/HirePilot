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
    create_user_oauth_only,
    delete_refresh_token,
    delete_user_refresh_tokens,
)
from db.models import User, UserRole
from schemas import Token
from security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    GOOGLE_CLIENT_ID,
)

# --- Constants ---
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Allowed email domains (STRICT AUTH CONTROL)
ALLOWED_EMAIL_DOMAINS = [
    "@incorta.com",
    "@gmail.com"
]


# --- Helper: Domain Validation ---

def is_email_allowed(email: str) -> bool:
    """
    Check if email belongs to allowed domains.
    """
    return any(email.endswith(domain) for domain in ALLOWED_EMAIL_DOMAINS)


# --- Helper Functions ---

def build_user_claims(user: User) -> Dict[str, Any]:
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
    }


def ensure_user_exists(user: Optional[User]) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def ensure_user_active(user: User) -> None:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )


def verify_google_token(id_token_str: str) -> Dict[str, Any]:
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


# --- AUTH FLOW ---

async def google_login(db: AsyncSession, id_token_str: str) -> Token:
    """
    Authenticate user using Google OAuth ID token.
    """

    payload = verify_google_token(id_token_str)
    email = payload.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in ID token"
        )

    # DOMAIN RESTRICTION (IMPORTANT SECURITY CHECK)
    if not is_email_allowed(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email domain not allowed. Allowed domains: {ALLOWED_EMAIL_DOMAINS}"
        )

    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found. Please register before logging in."
        )

    ensure_user_active(user)
    return await generate_auth_tokens(db, user)


# --- Refresh Token ---

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Token:
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


# --- User ---

async def get_current_user(db: AsyncSession, user_id: int) -> User:
    user = ensure_user_exists(await get_user_by_id(db, user_id))
    ensure_user_active(user)
    return user


# --- Logout ---

async def logout(db: AsyncSession, user_id: int, refresh_token: Optional[str] = None) -> Dict[str, str]:
    user = ensure_user_exists(await get_user_by_id(db, user_id))

    if refresh_token:
        token_hash = hash_token(refresh_token)
        await delete_refresh_token(db, token_hash)
        return {"message": "Logged out successfully"}

    revoked_count = await delete_user_refresh_tokens(db, user_id)
    return {"message": f"Logged out successfully. Revoked {revoked_count} token(s)."}


# --- Admin User Management ---

async def create_admin_user(db: AsyncSession, email: str, full_name: str, role: UserRole) -> User:

    if await get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email}' already exists"
        )

    return await create_user_oauth_only(db, email, full_name, role)


# --- Initial Setup ---

async def setup_initial_admin(db: AsyncSession, email: str, full_name: str, role: UserRole) -> User:

    admin_exists = await check_admin_exists(db)

    if admin_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already initialized."
        )

    if role != UserRole.HR_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Initial admin must be HR_MANAGER"
        )

    if await get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    return await create_user_oauth_only(db, email, full_name, UserRole.HR_MANAGER)