"""
User Management API router.
Handles listing, updating, and deactivating users (HR Manager only).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from controllers.services.auth_dependencies import require_hr_manager
from models.tables.user import User
from models.schemas.user_schemas import User as UserSchema, UserUpdate

from models.crud import get_users, get_user_by_id, update_user


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/users",
    tags=["user-management"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired credentials"},
        403: {"description": "Forbidden - HR Manager role required"},
    }
)


# ============================================================================
# Endpoints
# ============================================================================

################################ List All Users ########################################
@router.get(
    "",
    response_model=List[UserSchema],
    status_code=status.HTTP_200_OK,
    summary="List All Users",
    description="Get all users in the system (HR managers only)"
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> List[User]:
    """
    Get all users with pagination.
    
    Authentication:
        Required - HR Manager role only
    
    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100)
    
    Returns:
        List of user objects
    """
    return await get_users(db, skip=skip, limit=limit)


################################ Get User by ID ########################################
@router.get(
    "/{user_id}",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Get User by ID",
    description="Get a specific user by their ID (HR managers only)"
)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get a specific user by ID.
    
    Authentication:
        Required - HR Manager role only
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user


################################ Update User ########################################
@router.put(
    "/{user_id}",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Update User",
    description="Update a user's information (HR managers only)"
)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Update a user's information.
    
    Authentication:
        Required - HR Manager role only
    
    Request body (all fields optional):
    - email: New email address
    - full_name: New full name
    - role: New role (hr_manager or hiring_manager)
    - is_active: Active status
    
    Raises:
        HTTPException(404): User not found
    """
    updated_user = await update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return updated_user


################################ Deactivate User ########################################
@router.patch(
    "/{user_id}/deactivate",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Deactivate User",
    description="Deactivate a user's account (HR managers only)"
)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Deactivate a user's account.
    
    Authentication:
        Required - HR Manager role only
    
    Raises:
        HTTPException(404): User not found
        HTTPException(400): Cannot deactivate yourself
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    deactivation = UserUpdate(is_active=False)
    updated_user = await update_user(db, user_id, deactivation)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return updated_user


################################ Activate User ########################################
@router.patch(
    "/{user_id}/activate",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Activate User",
    description="Re-activate a deactivated user's account (HR managers only)"
)
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_hr_manager()),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Re-activate a user's account.
    
    Authentication:
        Required - HR Manager role only
    
    Raises:
        HTTPException(404): User not found
    """
    activation = UserUpdate(is_active=True)
    updated_user = await update_user(db, user_id, activation)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return updated_user
