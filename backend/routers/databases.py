"""
Database management routes for multi-database support.

This module contains thin HTTP handlers that delegate to DatabaseService
for all business logic.
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from models import (
    DatabaseCreate, DatabaseUpdate, DatabaseResponse,
    DatabaseListResponse, ViewerResponse
)
from auth import get_current_user
from utils import error_payload
from services.database_service import (
    database_service,
    DatabaseServiceError,
    DatabaseNotFoundError,
    DatabaseLimitReachedError,
    DuplicateNameError,
    CannotDeleteError,
    DatabaseInUseError,
    DatabaseCreateError,
    ViewerLaunchError,
    NoDatabasesError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/databases", tags=["databases"])


def handle_service_error(e: DatabaseServiceError) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    status_map = {
        "NOT_FOUND": 404,
        "LIMIT_REACHED": 400,
        "DUPLICATE_NAME": 400,
        "CANNOT_DELETE": 400,
        "DATABASE_IN_USE": 400,
        "DB_CREATE_FAILED": 500,
        "VIEWER_LAUNCH_FAILED": 500,
        "NO_DATABASES": 400,
    }
    status_code = status_map.get(e.code, 500)
    return HTTPException(
        status_code=status_code,
        detail=error_payload(e.code, e.message, e.details if e.details else None)
    )


# =============================================================================
# List and Create
# =============================================================================

@router.get("", response_model=DatabaseListResponse)
async def list_databases(user: dict = Depends(get_current_user)):
    """List all databases for the current user."""
    try:
        databases, total_size, default_id = await database_service.list_for_user(user)
        return DatabaseListResponse(
            databases=databases,
            total_size_mb=total_size,
            default_database_id=default_id
        )
    except DatabaseServiceError as e:
        raise handle_service_error(e)


@router.post("", response_model=DatabaseResponse)
async def create_database(
    data: DatabaseCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new database for the current user."""
    try:
        return await database_service.create(data, user)
    except DatabaseServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Get, Update, Delete
# =============================================================================

@router.get("/{database_id}", response_model=DatabaseResponse)
async def get_database(database_id: str, user: dict = Depends(get_current_user)):
    """Get details for a specific database."""
    try:
        db_entry, stats = await database_service.get_by_id(database_id, user)
        return database_service.to_response(db_entry, str(user["_id"]), stats)
    except DatabaseServiceError as e:
        raise handle_service_error(e)


@router.patch("/{database_id}", response_model=DatabaseResponse)
async def update_database(
    database_id: str,
    data: DatabaseUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a database's name, description, or default status."""
    try:
        return await database_service.update(database_id, data, user)
    except DatabaseServiceError as e:
        raise handle_service_error(e)


@router.delete("/{database_id}")
async def delete_database(database_id: str, user: dict = Depends(get_current_user)):
    """Delete a database. Cannot delete the last or default database."""
    try:
        await database_service.delete(database_id, user)
        return {"success": True, "message": "Database deleted"}
    except DatabaseServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Viewer
# =============================================================================

@router.post("/viewer", response_model=ViewerResponse)
async def launch_viewer_all_databases(user: dict = Depends(get_current_user)):
    """Launch MongoDB viewer with access to all user's databases."""
    try:
        return await database_service.launch_viewer(user)
    except DatabaseServiceError as e:
        raise handle_service_error(e)


@router.post("/{database_id}/viewer", response_model=ViewerResponse)
async def launch_viewer_single_database(database_id: str, user: dict = Depends(get_current_user)):
    """Launch MongoDB viewer for a specific database (deprecated - use /viewer instead)."""
    try:
        return await database_service.launch_viewer(user, database_id)
    except DatabaseServiceError as e:
        raise handle_service_error(e)
