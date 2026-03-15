"""
FastAPI dependencies for authentication and authorization.
"""

from .auth_dependencies import (
    oauth2_scheme,
    get_current_user,
    require_role,
    require_hr_manager,
    require_hiring_manager,
    require_any_manager
)

__all__ = [
    "oauth2_scheme",
    "get_current_user",
    "require_role",
    "require_hr_manager",
    "require_hiring_manager",
    "require_any_manager"
]
