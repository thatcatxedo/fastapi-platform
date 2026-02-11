"""
Database management routes for multi-database support.

This module contains thin HTTP handlers that delegate to DatabaseService
for all business logic. Includes the In-App MongoDB Explorer endpoints
for browsing collections and documents.
"""
import json
import logging

from fastapi import APIRouter, HTTPException, Depends, Query

from models import (
    DatabaseCreate, DatabaseUpdate, DatabaseResponse,
    DatabaseListResponse, ViewerResponse,
    CollectionListResponse, DocumentListResponse
)
from auth import get_current_user
from utils import error_payload, serialize_mongo_doc
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
# Explorer — In-App MongoDB browsing
# =============================================================================

# Dangerous MongoDB operators that must not appear in user-supplied filters.
BLOCKED_FILTER_OPERATORS = {"$where", "$function", "$accumulator", "$expr"}


def _validate_filter(obj, depth: int = 0) -> None:
    """Reject filters containing dangerous operators (recursive)."""
    if depth > 10:
        raise ValueError("Filter too deeply nested")
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.startswith("$") and key in BLOCKED_FILTER_OPERATORS:
                raise ValueError(f"Operator {key} is not allowed in filters")
            _validate_filter(value, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _validate_filter(item, depth + 1)


@router.get("/{database_id}/collections", response_model=CollectionListResponse)
async def list_collections(
    database_id: str,
    user: dict = Depends(get_current_user)
):
    """List collections with stats for a user database."""
    try:
        # Verify the database belongs to the user
        db_entry = database_service.get_database_entry(
            user.get("databases", []), database_id
        )
    except DatabaseServiceError as e:
        raise handle_service_error(e)

    user_id = str(user["_id"])
    stats = await database_service.get_collection_stats(user_id, database_id)

    if stats is None:
        raise HTTPException(
            status_code=500,
            detail=error_payload("STATS_ERROR", "Failed to retrieve collection stats")
        )

    return CollectionListResponse(
        database_id=database_id,
        database_name=db_entry["name"],
        collections=stats["collections"],
        total_collections=stats["total_collections"],
        total_documents=stats["total_documents"],
        total_size_mb=stats["total_size_mb"],
    )


@router.get("/{database_id}/{collection}/documents", response_model=DocumentListResponse)
async def list_documents(
    database_id: str,
    collection: str,
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str = Query("_id"),
    sort_dir: int = Query(-1, ge=-1, le=1),
    filter: str = Query(None, alias="filter"),
):
    """Paginated document listing for a collection (read-only)."""
    # Verify the database belongs to the user
    try:
        database_service.get_database_entry(
            user.get("databases", []), database_id
        )
    except DatabaseServiceError as e:
        raise handle_service_error(e)

    user_id = str(user["_id"])
    db_name = database_service.get_mongo_db_name(user_id, database_id)
    user_db = database_service.client[db_name]

    # Verify collection exists
    try:
        existing = await user_db.list_collection_names()
    except Exception as exc:
        logger.error(f"Failed to list collections for {db_name}: {exc}")
        raise HTTPException(status_code=500, detail=error_payload(
            "DB_ERROR", "Failed to access database"
        ))

    if collection not in existing:
        raise HTTPException(status_code=404, detail=error_payload(
            "NOT_FOUND", f"Collection '{collection}' not found"
        ))

    # Parse and validate filter
    query: dict = {}
    if filter:
        try:
            query = json.loads(filter)
            if not isinstance(query, dict):
                raise ValueError("Filter must be a JSON object")
            _validate_filter(query)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=error_payload(
                "INVALID_FILTER", "Filter is not valid JSON"
            ))
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=error_payload(
                "INVALID_FILTER", str(ve)
            ))

    coll = user_db[collection]
    sort_direction = sort_dir if sort_dir != 0 else -1
    skip = (page - 1) * page_size

    try:
        total = await coll.count_documents(query, maxTimeMS=2000)
        cursor = (
            coll.find(query)
            .sort(sort_field, sort_direction)
            .skip(skip)
            .limit(page_size)
        )
        # Apply a 2-second server-side timeout
        cursor.max_time_ms(2000)
        raw_docs = await cursor.to_list(length=page_size)
    except Exception as exc:
        logger.error(f"Document query failed on {db_name}.{collection}: {exc}")
        raise HTTPException(status_code=400, detail=error_payload(
            "QUERY_ERROR", "Query failed — check your filter syntax"
        ))

    documents = [serialize_mongo_doc(doc) for doc in raw_docs]

    return DocumentListResponse(
        documents=documents,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
    )


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
