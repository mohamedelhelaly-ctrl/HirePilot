from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import bcrypt

from db.models import User, UserRole
from schemas import UserCreate, UserUpdate


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create a new user with hashed password."""
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user information."""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def check_admin_exists(db: AsyncSession) -> bool:
    """
    Check if any HR_MANAGER user exists in the database.
    
    Used for bootstrap checks during initial setup.
    
    Args:
        db: Database session
        
    Returns:
        True if at least one HR_MANAGER exists, False otherwise
    """
    result = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.HR_MANAGER)
    )
    count = result.scalar() or 0
    return count > 0


async def get_admin_count(db: AsyncSession) -> int:
    """
    Get total count of HR_MANAGER users in the database.
    
    Used for monitoring and setup verification.
    
    Args:
        db: Database session
        
    Returns:
        Count of HR_MANAGER users
    """
    result = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.HR_MANAGER)
    )
    return result.scalar() or 0

