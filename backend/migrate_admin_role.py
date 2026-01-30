"""
Migration script to set the first user as admin if no admin exists.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

async def migrate_admin_role(client: AsyncIOMotorClient):
    """Set first user as admin if no admin exists"""
    db = client.fastapi_platform_db
    users_collection = db.users
    
    # Check if any admin exists
    admin = await users_collection.find_one({"is_admin": True})
    if admin:
        logger.info(f"Admin user already exists: {admin.get('username')}")
        return
    
    # Find earliest user and make them admin
    first_user = await users_collection.find_one(sort=[("created_at", 1)])
    if first_user:
        await users_collection.update_one(
            {"_id": first_user["_id"]},
            {"$set": {"is_admin": True}}
        )
        logger.info(f"Set {first_user['username']} as admin (first user)")
    else:
        logger.info("No users found, first signup will become admin")
