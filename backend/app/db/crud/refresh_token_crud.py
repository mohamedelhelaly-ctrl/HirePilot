from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional
from datetime import datetime

from db.models import RefreshToken


async def create_refresh_token(
    db: AsyncSession,
    user_id: int,
    token_hash: str,
    expires_at: datetime
) -> RefreshToken:
    """Create a new refresh token."""
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def get_refresh_token_by_hash(
    db: AsyncSession,
    token_hash: str
) -> Optional[RefreshToken]:
    """Get refresh token by hash."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token_hash: str) -> bool:
    """Delete a refresh token."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_expired_refresh_tokens(db: AsyncSession) -> int:
    """Delete all expired refresh tokens."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
    )
    await db.commit()
    return result.rowcount


async def delete_user_refresh_tokens(db: AsyncSession, user_id: int) -> int:
    """Delete all refresh tokens for a user."""
    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    await db.commit()
    return result.rowcount


