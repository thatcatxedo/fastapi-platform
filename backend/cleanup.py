"""
Background job to clean up inactive user apps
"""
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
import asyncio
import logging
from deployment import delete_app_deployment

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.fastapi_platform_db
apps_collection = db.apps
users_collection = db.users

INACTIVITY_THRESHOLD_HOURS = int(os.getenv("INACTIVITY_THRESHOLD_HOURS", "24"))

async def cleanup_inactive_apps():
    """Delete apps that haven't been accessed in the threshold period"""
    threshold = datetime.utcnow() - timedelta(hours=INACTIVITY_THRESHOLD_HOURS)
    
    # Find inactive apps
    inactive_apps = []
    async for app in apps_collection.find({
        "status": {"$in": ["running", "deploying"]},
        "last_activity": {"$lt": threshold}
    }):
        inactive_apps.append(app)
    
    logger.info(f"Found {len(inactive_apps)} inactive apps to clean up")
    
    for app in inactive_apps:
        try:
            # Get user for deployment deletion
            user = await users_collection.find_one({"_id": app["user_id"]})
            if not user:
                logger.warning(f"User not found for app {app['app_id']}, skipping")
                continue
            
            # Delete Kubernetes resources
            await delete_app_deployment(app, user)
            
            # Mark as deleted in database
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": "deleted", "deleted_at": datetime.utcnow()}}
            )
            
            logger.info(f"Cleaned up inactive app {app['app_id']}")
        except Exception as e:
            logger.error(f"Error cleaning up app {app.get('app_id', 'unknown')}: {e}")

async def run_cleanup_loop():
    """Run cleanup job periodically"""
    while True:
        try:
            await cleanup_inactive_apps()
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
        
        # Run every hour
        await asyncio.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_cleanup_loop())
