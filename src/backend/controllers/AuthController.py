from .BaseController import BaseController

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

# External imports

from models.database import get_db

from models.schemas import (
    LoginRequest,
    GoogleLoginRequest,
    TokenRefreshRequest,
    LogoutRequest,
    AdminUserCreate,
    Token,
    LogoutResponse,
    User
)

# Should be removed
from .services.auth_service import (
    email_login,
    google_login,
    refresh_access_token,
    logout,
    create_admin_user,
    setup_initial_admin
)

# Should be removed
from .services.auth_dependencies import get_current_user, require_hr_manager

#####################################################################################
#####################################################################################

class AuthController(BaseController):
    def __init__(self):
        super().__init__()
    
    async def login(self, login_request: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
        return await email_login(login_request, db)
    
    async def google_auth(self, request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
        return await google_login(request, db)
    
    async def refresh_token(self, request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
        return await refresh_access_token(db, request.refresh_token)
    
    def get_current_user_profile(self, current_user: User = Depends(get_current_user)) -> User:
        return current_user
    
    async def logout_user(self, request: LogoutRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> LogoutResponse:
        result = await logout(
            db=db,
            user_id=current_user.id,
            refresh_token=request.refresh_token
        )
        return LogoutResponse(message=result["message"])
    
    async def create_user_admin(self, request: AdminUserCreate, current_user: User = Depends(require_hr_manager()), db: AsyncSession = Depends(get_db)) -> User:
        return await create_admin_user(
            db=db,
            email=request.email,
            full_name=request.full_name,
            role=request.role
        )
    
    async def setup_system(self, request: AdminUserCreate, db: AsyncSession = Depends(get_db)) -> User:
        return await setup_initial_admin(
            db=db,
            email=request.email,
            full_name=request.full_name,
            role=request.role
        )

