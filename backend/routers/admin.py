"""
Admin routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from bson import ObjectId
import logging

from models import AdminSettingsUpdate, UserSignup, UserResponse
from auth import require_admin, hash_password
from routers.auth import build_user_response
from database import (
    users_collection, apps_collection, templates_collection,
    settings_collection, viewer_instances_collection, client
)
from utils import error_payload
from deployment import delete_app_deployment, delete_mongo_viewer_resources

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/settings")
async def get_admin_settings(admin: dict = Depends(require_admin)):
    settings = await settings_collection.find_one({"_id": "global"})
    return {
        "allow_signups": settings.get("allow_signups", True) if settings else True
    }


@router.put("/settings")
async def update_admin_settings(
    settings: AdminSettingsUpdate,
    admin: dict = Depends(require_admin)
):
    await settings_collection.update_one(
        {"_id": "global"},
        {"$set": {
            "allow_signups": settings.allow_signups,
            "updated_at": datetime.utcnow(),
            "updated_by": admin["_id"]
        }},
        upsert=True
    )
    return {"success": True}


@router.get("/users")
async def list_all_users(admin: dict = Depends(require_admin)):
    users = []
    async for user in users_collection.find().sort("created_at", -1):
        app_count = await apps_collection.count_documents({"user_id": user["_id"]})
        running_app_count = await apps_collection.count_documents({"user_id": user["_id"], "status": "running"})
        users.append({
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"].isoformat(),
            "is_admin": user.get("is_admin", False),
            "app_count": app_count,
            "running_app_count": running_app_count
        })
    return users


@router.get("/stats")
async def get_platform_stats(admin: dict = Depends(require_admin)):
    user_count = await users_collection.count_documents({})
    app_count = await apps_collection.count_documents({})
    running_apps = await apps_collection.count_documents({"status": "running"})
    template_count = await templates_collection.count_documents({})

    recent_users = await users_collection.find().sort("created_at", -1).limit(5).to_list(5)
    recent_apps = await apps_collection.find().sort("created_at", -1).limit(5).to_list(5)

    # MongoDB stats
    mongo_stats = {}
    try:
        # Get list of user databases
        db_list = await client.list_database_names()
        user_dbs = [db for db in db_list if db.startswith("user_")]

        total_storage = 0
        total_collections = 0
        total_documents = 0

        for db_name in user_dbs:
            try:
                db = client[db_name]
                stats = await db.command("dbStats")
                total_storage += stats.get("storageSize", 0)
                total_collections += stats.get("collections", 0)
                total_documents += stats.get("objects", 0)
            except Exception:
                pass

        # Platform DB stats
        platform_db = client.fastapi_platform_db
        platform_stats = await platform_db.command("dbStats")

        mongo_stats = {
            "user_databases": len(user_dbs),
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
            "total_collections": total_collections,
            "total_documents": total_documents,
            "platform_storage_mb": round(platform_stats.get("storageSize", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.warning(f"Failed to get MongoDB stats: {e}")
        mongo_stats = {"error": str(e)}

    return {
        "users": user_count,
        "apps": app_count,
        "running_apps": running_apps,
        "templates": template_count,
        "mongo": mongo_stats,
        "recent_signups": [
            {"username": u["username"], "created_at": u["created_at"].isoformat()}
            for u in recent_users
        ],
        "recent_deploys": [
            {"name": a["name"], "app_id": a["app_id"], "created_at": a["created_at"].isoformat()}
            for a in recent_apps
        ]
    }


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
    user_data: UserSignup,
    admin: dict = Depends(require_admin)
):
    # Reuse signup logic but skip signups_allowed check
    existing = await users_collection.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.utcnow(),
        "is_admin": False  # Admin-created users are not admins
    }
    result = await users_collection.insert_one(user_doc)
    
    # Create MongoDB user
    try:
        from mongo_users import create_mongo_user, encrypt_password
        mongo_username, mongo_password = await create_mongo_user(client, str(result.inserted_id))
        await users_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"mongo_password_encrypted": encrypt_password(mongo_password)}}
        )
    except Exception as e:
        logger.error(f"Failed to create MongoDB user: {e}")
    
    user = await users_collection.find_one({"_id": result.inserted_id})
    return build_user_response(user)


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: str,
    admin: dict = Depends(require_admin)
):
    # Prevent self-deletion
    if str(admin["_id"]) == user_id:
        raise HTTPException(
            status_code=400,
            detail=error_payload("CANNOT_DELETE_SELF", "Cannot delete your own account")
        )
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=404,
            detail=error_payload("USER_NOT_FOUND", "User not found")
        )
    
    # Delete user's apps (K8s resources + DB records)
    async for app in apps_collection.find({"user_id": ObjectId(user_id)}):
        try:
            await delete_app_deployment(app, user)
        except Exception as e:
            logger.warning(f"Failed to delete app {app['app_id']}: {e}")
    
    await apps_collection.delete_many({"user_id": ObjectId(user_id)})
    
    # Delete MongoDB user
    try:
        from mongo_users import delete_mongo_user
        await delete_mongo_user(client, user_id)
    except Exception as e:
        logger.warning(f"Failed to delete MongoDB user for {user_id}: {e}")
    
    # Delete user's database
    try:
        await client.drop_database(f"user_{user_id}")
    except Exception as e:
        logger.warning(f"Failed to drop database for {user_id}: {e}")
    
    # Delete viewer instance and resources
    viewer = await viewer_instances_collection.find_one({"user_id": ObjectId(user_id)})
    if viewer:
        try:
            await delete_mongo_viewer_resources(user_id)
        except Exception as e:
            logger.warning(f"Failed to delete viewer resources for {user_id}: {e}")
        await viewer_instances_collection.delete_many({"user_id": ObjectId(user_id)})
    
    # Delete user record
    await users_collection.delete_one({"_id": ObjectId(user_id)})
    
    return {"success": True, "deleted_user_id": user_id}
