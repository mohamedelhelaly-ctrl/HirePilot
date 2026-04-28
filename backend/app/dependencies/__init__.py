"""
FastAPI dependencies for authentication and authorization.
"""

from .auth_dependencies import (
    get_current_user,
    require_role,
    require_hr_manager,
    require_hiring_manager,
    require_any_manager
)

__all__ = [
    "get_current_user",
    "require_role",
    "require_hr_manager",
    "require_hiring_manager",
    "require_any_manager"
]
