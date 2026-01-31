"""
Database management routes for multi-database support
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid
import logging

from models import (
    DatabaseCreate, DatabaseUpdate, DatabaseResponse,
    DatabaseListResponse, ViewerResponse
)
from auth import get_current_user
from database import users_collection, apps_collection, client
from mongo_users import (
    create_mongo_user_for_database,
    delete_mongo_user_for_database,
    encrypt_password,
    decrypt_password,
    get_mongo_db_name,
    generate_mongo_password
)
from utils import error_payload
from config import APP_DOMAIN

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/databases", tags=["databases"])

MAX_DATABASES_PER_USER = 10


async def get_database_stats(user_id: str, database_id: str) -> dict:
    """Get stats for a specific user database."""
    db_name = get_mongo_db_name(user_id, database_id)
    user_db = client[db_name]

    try:
        collection_names = await user_db.list_collection_names()
        db_stats = await user_db.command("dbStats")

        return {
            "total_collections": len(collection_names),
            "total_documents": db_stats.get("objects", 0),
            "total_size_bytes": db_stats.get("dataSize", 0),
            "total_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.warning(f"Error getting stats for {db_name}: {e}")
        return {
            "total_collections": 0,
            "total_documents": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0
        }


def format_datetime(dt) -> str:
    """Format datetime to ISO string."""
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return str(dt)


@router.get("", response_model=DatabaseListResponse)
async def list_databases(user: dict = Depends(get_current_user)):
    """List all databases for the current user."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    result = []
    total_size = 0

    for db_entry in databases:
        stats = await get_database_stats(user_id, db_entry["id"])
        total_size += stats["total_size_mb"]

        result.append(DatabaseResponse(
            id=db_entry["id"],
            name=db_entry["name"],
            description=db_entry.get("description"),
            is_default=db_entry.get("is_default", False),
            mongo_database=get_mongo_db_name(user_id, db_entry["id"]),
            created_at=format_datetime(db_entry["created_at"]),
            total_collections=stats["total_collections"],
            total_documents=stats["total_documents"],
            total_size_mb=stats["total_size_mb"]
        ))

    return DatabaseListResponse(
        databases=result,
        total_size_mb=round(total_size, 2),
        default_database_id=user.get("default_database_id", "default")
    )


@router.post("", response_model=DatabaseResponse)
async def create_database(
    data: DatabaseCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new database for the current user."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    # Check limit
    if len(databases) >= MAX_DATABASES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=error_payload("LIMIT_REACHED", f"Maximum {MAX_DATABASES_PER_USER} databases allowed")
        )

    # Check for duplicate name
    if any(db["name"].lower() == data.name.lower() for db in databases):
        raise HTTPException(
            status_code=400,
            detail=error_payload("DUPLICATE_NAME", "A database with this name already exists")
        )

    # Generate unique ID
    database_id = str(uuid.uuid4())[:8]

    # Create MongoDB user for this database
    try:
        _, mongo_password = await create_mongo_user_for_database(
            client, user_id, database_id
        )
    except Exception as e:
        logger.error(f"Failed to create MongoDB user: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_payload("DB_CREATE_FAILED", "Failed to create database")
        )

    # Create database entry
    now = datetime.utcnow()
    new_db = {
        "id": database_id,
        "name": data.name,
        "description": data.description,
        "mongo_password_encrypted": encrypt_password(mongo_password),
        "created_at": now,
        "is_default": False
    }

    # Add to user's databases
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$push": {"databases": new_db}}
    )

    return DatabaseResponse(
        id=database_id,
        name=data.name,
        description=data.description,
        is_default=False,
        mongo_database=get_mongo_db_name(user_id, database_id),
        created_at=format_datetime(now),
        total_collections=0,
        total_documents=0,
        total_size_mb=0
    )


@router.get("/{database_id}", response_model=DatabaseResponse)
async def get_database(database_id: str, user: dict = Depends(get_current_user)):
    """Get details for a specific database."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    db_entry = next((db for db in databases if db["id"] == database_id), None)
    if not db_entry:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Database not found"))

    stats = await get_database_stats(user_id, database_id)

    return DatabaseResponse(
        id=db_entry["id"],
        name=db_entry["name"],
        description=db_entry.get("description"),
        is_default=db_entry.get("is_default", False),
        mongo_database=get_mongo_db_name(user_id, database_id),
        created_at=format_datetime(db_entry["created_at"]),
        **stats
    )


@router.patch("/{database_id}", response_model=DatabaseResponse)
async def update_database(
    database_id: str,
    data: DatabaseUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a database's name, description, or default status."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    db_index = next((i for i, db in enumerate(databases) if db["id"] == database_id), None)
    if db_index is None:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Database not found"))

    update_ops = {}

    if data.name is not None:
        # Check for duplicate name
        if any(db["name"].lower() == data.name.lower() and db["id"] != database_id for db in databases):
            raise HTTPException(
                status_code=400,
                detail=error_payload("DUPLICATE_NAME", "A database with this name already exists")
            )
        update_ops[f"databases.{db_index}.name"] = data.name

    if data.description is not None:
        update_ops[f"databases.{db_index}.description"] = data.description

    if data.is_default is True:
        # Clear other defaults and set this one
        for i, db in enumerate(databases):
            update_ops[f"databases.{i}.is_default"] = (i == db_index)
        update_ops["default_database_id"] = database_id

    if update_ops:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": update_ops}
        )

    # Fetch updated user and return database
    updated_user = await users_collection.find_one({"_id": user["_id"]})
    db_entry = updated_user["databases"][db_index]
    stats = await get_database_stats(user_id, database_id)

    return DatabaseResponse(
        id=db_entry["id"],
        name=db_entry["name"],
        description=db_entry.get("description"),
        is_default=db_entry.get("is_default", False),
        mongo_database=get_mongo_db_name(user_id, database_id),
        created_at=format_datetime(db_entry["created_at"]),
        **stats
    )


@router.delete("/{database_id}")
async def delete_database(database_id: str, user: dict = Depends(get_current_user)):
    """Delete a database. Cannot delete the last or default database."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    if len(databases) <= 1:
        raise HTTPException(
            status_code=400,
            detail=error_payload("CANNOT_DELETE", "Cannot delete the last database")
        )

    db_entry = next((db for db in databases if db["id"] == database_id), None)
    if not db_entry:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Database not found"))

    if db_entry.get("is_default"):
        raise HTTPException(
            status_code=400,
            detail=error_payload("CANNOT_DELETE", "Cannot delete the default database. Set another database as default first.")
        )

    # Check if any apps use this database
    apps_using_db = await apps_collection.count_documents({
        "user_id": user["_id"],
        "database_id": database_id,
        "status": {"$ne": "deleted"}
    })

    if apps_using_db > 0:
        raise HTTPException(
            status_code=400,
            detail=error_payload(
                "DATABASE_IN_USE",
                f"{apps_using_db} app(s) are using this database. Update them to use a different database first."
            )
        )

    # Delete MongoDB user
    try:
        await delete_mongo_user_for_database(client, user_id, database_id)
    except Exception as e:
        logger.warning(f"Failed to delete MongoDB user for database {database_id}: {e}")

    # Drop the MongoDB database
    db_name = get_mongo_db_name(user_id, database_id)
    try:
        await client.drop_database(db_name)
        logger.info(f"Dropped MongoDB database {db_name}")
    except Exception as e:
        logger.warning(f"Failed to drop database {db_name}: {e}")

    # Remove from user's databases array
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$pull": {"databases": {"id": database_id}}}
    )

    return {"success": True, "message": "Database deleted"}


@router.post("/{database_id}/viewer", response_model=ViewerResponse)
async def launch_viewer(database_id: str, user: dict = Depends(get_current_user)):
    """Launch MongoDB viewer for a specific database."""
    user_id = str(user["_id"])
    databases = user.get("databases", [])

    db_entry = next((db for db in databases if db["id"] == database_id), None)
    if not db_entry:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "Database not found"))

    # Generate viewer credentials (basic auth for mongo-express)
    viewer_username = "admin"
    viewer_password = generate_mongo_password()[:12]

    try:
        from deployment.viewer import create_mongo_viewer_resources, get_mongo_viewer_status

        # Create/update viewer resources with this database
        await create_mongo_viewer_resources(
            user_id, user, viewer_username, viewer_password,
            database_id=database_id
        )

        # Get status
        status = await get_mongo_viewer_status(user_id)
        viewer_url = f"http://mongo-{user_id}.{APP_DOMAIN}"

        return ViewerResponse(
            url=viewer_url,
            username=viewer_username,
            password=viewer_password,
            password_provided=True,
            ready=status.get("ready", False) if status else False,
            pod_status=status.get("pod_status") if status else None
        )
    except Exception as e:
        logger.error(f"Failed to launch viewer for database {database_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_payload("VIEWER_LAUNCH_FAILED", str(e))
        )
