"""
FastAPI dependency injection for authentication.
Provides reusable dependencies for route protection and role authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Callable

from db.database import get_db
from db.models import UserRole, User
from security import decode_access_token
from services.auth_service import get_current_user as service_get_current_user


# ============================================================================
# OAuth2 Scheme
# ============================================================================

# OAuth2 password bearer scheme for Swagger documentation
# Points to the login endpoint where tokens are obtained
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ============================================================================
# Get Current User Dependency
# ============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency that validates JWT access token and loads current user.
    
    Steps:
    1. Decode JWT access token from Authorization header
    2. Extract user_id from token payload
    3. Load user from database
    4. Verify user is active
    5. Return User object
    
    Args:
        token: JWT access token from Authorization header (via oauth2_scheme)
        db: Database session dependency
        
    Returns:
        User model instance
        
    Raises:
        HTTPException(401): If token is invalid, expired, or user not found
        HTTPException(403): If user is inactive
        
    Usage:
        @router.get("/me")
        async def get_profile(current_user: User = Depends(get_current_user)):
            return current_user
    """
    # Step 1: Decode JWT access token
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 2: Extract user_id from token payload
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3-5: Load user from database, verify active status
    user = await service_get_current_user(db, user_id)
    
    return user


# ============================================================================
# Role-Based Authorization
# ============================================================================

def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    FastAPI dependency factory for role-based authorization.
    Returns a dependency function that checks if current user has required role.
    
    Steps:
    1. Get current user via get_current_user dependency
    2. Check if user's role is in allowed_roles list
    3. Raise HTTP 403 Forbidden if role not authorized
    
    Args:
        allowed_roles: List of UserRole enums that are allowed
        
    Returns:
        Async function that acts as FastAPI dependency
        
    Raises:
        HTTPException(403): If user's role not in allowed_roles
        
    Usage:
        # HR manager only
        @router.get("/admin/users")
        async def admin_users(
            current_user: User = Depends(require_role([UserRole.HR_MANAGER]))
        ):
            return current_user
    """
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        """
        Check that current user has one of the required roles.
        
        Steps:
        1. Get current user
        2. Verify user's role is in allowed_roles
        3. Return user if authorized
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            User instance if authorized
            
        Raises:
            HTTPException(403): If user role not authorized
        """
        # Step 1: Current user already obtained via dependency
        # Step 2: Check role authorization
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role.value}' is not authorized for this resource. "
                       f"Required roles: {[r.value for r in allowed_roles]}"
            )
        
        # Step 3: Return user if authorized
        return current_user
    
    return check_role


# ============================================================================
# Convenience Role Checkers
# ============================================================================

def require_hr_manager() -> Callable:
    """
    Convenience dependency that restricts access to HR managers only.
    
    Usage:
        @router.get("/requisitions")
        async def list_requisitions(
            current_user: User = Depends(require_hr_manager())
        ):
            return "HR only"
    """
    return require_role([UserRole.HR_MANAGER])


def require_hiring_manager() -> Callable:
    """
    Convenience dependency that restricts access to hiring managers only.
    
    Usage:
        @router.get("/my-requisitions")
        async def list_my_requisitions(
            current_user: User = Depends(require_hiring_manager())
        ):
            return "Hiring manager only"
    """
    return require_role([UserRole.HIRING_MANAGER])


def require_any_manager() -> Callable:
    """
    Convenience dependency that restricts access to any manager role.
    
    Usage:
        @router.get("/dashboard")
        async def dashboard(
            current_user: User = Depends(require_any_manager())
        ):
            return "Any manager only"
    """
    return require_role([UserRole.HR_MANAGER, UserRole.HIRING_MANAGER])
