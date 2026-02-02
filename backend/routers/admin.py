"""
Admin routes for FastAPI Platform.

This module contains thin HTTP handlers that delegate to AdminService
for all business logic.
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from models import AdminSettingsUpdate, AdminStatusUpdate, UserSignup, UserResponse
from auth import require_admin
from routers.auth import build_user_response
from utils import error_payload
from services.admin_service import (
    admin_service,
    AdminServiceError,
    UserNotFoundError,
    CannotDemoteSelfError,
    CannotRemoveLastAdminError,
    CannotDeleteSelfError,
    InvalidSettingsError,
    UserExistsError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def handle_service_error(e: AdminServiceError) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    status_map = {
        "USER_NOT_FOUND": 404,
        "CANNOT_DEMOTE_SELF": 400,
        "CANNOT_REMOVE_LAST_ADMIN": 400,
        "CANNOT_DELETE_SELF": 400,
        "INVALID_SETTINGS": 400,
        "USER_EXISTS": 400,
    }
    status_code = status_map.get(e.code, 500)
    return HTTPException(
        status_code=status_code,
        detail=error_payload(e.code, e.message, e.details if e.details else None)
    )


# =============================================================================
# Settings
# =============================================================================

@router.get("/settings")
async def get_admin_settings(admin: dict = Depends(require_admin)):
    """Get platform settings."""
    return await admin_service.get_settings()


@router.put("/settings")
async def update_admin_settings(
    settings: AdminSettingsUpdate,
    admin: dict = Depends(require_admin)
):
    """Update platform settings."""
    try:
        await admin_service.update_settings(settings, admin)
        return {"success": True}
    except AdminServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# User Management
# =============================================================================

@router.get("/users")
async def list_all_users(admin: dict = Depends(require_admin)):
    """List all users with app counts."""
    return await admin_service.list_users_with_stats()


@router.patch("/users/{user_id}/admin")
async def update_user_admin_status(
    user_id: str,
    status_update: AdminStatusUpdate,
    admin: dict = Depends(require_admin)
):
    """Promote or demote a user to/from admin status."""
    try:
        return await admin_service.update_admin_status(user_id, status_update, admin)
    except AdminServiceError as e:
        raise handle_service_error(e)


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
    user_data: UserSignup,
    admin: dict = Depends(require_admin)
):
    """Create a new user (admin action)."""
    try:
        user = await admin_service.create_user(user_data, admin)
        return build_user_response(user)
    except AdminServiceError as e:
        raise handle_service_error(e)


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    """Delete a user with cascade cleanup."""
    try:
        return await admin_service.delete_user(user_id, admin)
    except AdminServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Statistics
# =============================================================================

@router.get("/stats")
async def get_platform_stats(admin: dict = Depends(require_admin)):
    """Get platform statistics."""
    return await admin_service.get_platform_stats()
