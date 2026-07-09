"""
CRUD operations for Google OAuth credentials.
Handles creation, retrieval, update, and deletion of encrypted Google OAuth tokens.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from typing import Optional
from datetime import datetime, timedelta, timezone

from models.tables.google_oauth_credential import GoogleOAuthCredential
from controllers.services.security import encrypt_token, decrypt_token


async def create_google_oauth_credential(
    db: AsyncSession,
    user_id: int,
    google_account_email: str,
    access_token: str,
    refresh_token: str,
    token_expiry: datetime
) -> GoogleOAuthCredential:
    """
    Create a new Google OAuth credential record with encrypted tokens.
    
    Args:
        db: Database session
        user_id: User ID this credential belongs to
        google_account_email: Google account email address
        access_token: Plaintext access token (will be encrypted)
        refresh_token: Plaintext refresh token (will be encrypted)
        token_expiry: UTC datetime when access token expires
        
    Returns:
        Created GoogleOAuthCredential instance
    """
    # Encrypt tokens before storage
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token)
    
    db_credential = GoogleOAuthCredential(
        user_id=user_id,
        google_account_email=google_account_email,
        access_token=encrypted_access_token,
        refresh_token=encrypted_refresh_token,
        token_expiry=token_expiry
    )
    db.add(db_credential)
    await db.commit()
    await db.refresh(db_credential)
    return db_credential


async def get_google_oauth_credential(
    db: AsyncSession,
    user_id: int
) -> Optional[GoogleOAuthCredential]:
    """
    Retrieve Google OAuth credential for a user.
    
    Args:
        db: Database session
        user_id: User ID to fetch credentials for
        
    Returns:
        GoogleOAuthCredential instance or None if not found
    """
    result = await db.execute(
        select(GoogleOAuthCredential).where(
            GoogleOAuthCredential.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_google_oauth_credential(
    db: AsyncSession,
    user_id: int,
    access_token: str,
    refresh_token: str,
    token_expiry: datetime
) -> Optional[GoogleOAuthCredential]:
    """
    Update Google OAuth tokens for a user (typically during token refresh).
    
    Args:
        db: Database session
        user_id: User ID to update
        access_token: New plaintext access token
        refresh_token: New plaintext refresh token
        token_expiry: New token expiry timestamp
        
    Returns:
        Updated GoogleOAuthCredential instance or None if not found
    """
    # Encrypt new tokens
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token)
    
    # Update the record
    await db.execute(
        update(GoogleOAuthCredential)
        .where(GoogleOAuthCredential.user_id == user_id)
        .values(
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_expiry=token_expiry,
            updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()
    
    # Return updated credential
    return await get_google_oauth_credential(db, user_id)


async def delete_google_oauth_credential(
    db: AsyncSession,
    user_id: int
) -> bool:
    """
    Delete Google OAuth credential for a user (e.g., on logout or account disconnection).
    
    Args:
        db: Database session
        user_id: User ID to delete credentials for
        
    Returns:
        True if credential was deleted, False if not found
    """
    result = await db.execute(
        delete(GoogleOAuthCredential).where(
            GoogleOAuthCredential.user_id == user_id
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_decrypted_access_token(
    db: AsyncSession,
    user_id: int
) -> Optional[str]:
    """
    Get decrypted access token for a user (for API calls).
    
    Args:
        db: Database session
        user_id: User ID to fetch token for
        
    Returns:
        Plaintext access token or None if credential not found
    """
    credential = await get_google_oauth_credential(db, user_id)
    if not credential:
        return None
    
    return decrypt_token(credential.access_token)


async def get_decrypted_refresh_token(
    db: AsyncSession,
    user_id: int
) -> Optional[str]:
    """
    Get decrypted refresh token for a user.
    
    Args:
        db: Database session
        user_id: User ID to fetch token for
        
    Returns:
        Plaintext refresh token or None if credential not found
    """
    credential = await get_google_oauth_credential(db, user_id)
    if not credential:
        return None
    
    return decrypt_token(credential.refresh_token)


async def store_google_oauth_credentials(
    db: AsyncSession,
    user_id: int,
    google_account_email: str,
    access_token: str,
    refresh_token: str,
    expires_in: int = 3600
) -> None:
    """
    Store Google OAuth credentials in database with encryption.
    
    This is a convenience function that creates or updates credentials
    based on whether they already exist for the user.
    
    Args:
        db: Database session
        user_id: User ID to store credentials for
        google_account_email: Google account email
        access_token: Plaintext access token
        refresh_token: Plaintext refresh token
        expires_in: Seconds until access token expires (default 1 hour)
    """
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    # Check if credential already exists
    existing = await get_google_oauth_credential(db, user_id)
    
    if existing:
        # Update existing credential
        await update_google_oauth_credential(
            db=db,
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )
    else:
        # Create new credential
        await create_google_oauth_credential(
            db=db,
            user_id=user_id,
            google_account_email=google_account_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )
