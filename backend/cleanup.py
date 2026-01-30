"""
Background job to clean up inactive user apps
"""
from datetime import datetime, timedelta
import os
import asyncio
import logging
from deployment import delete_app_deployment, delete_mongo_viewer_resources
from database import client, apps_collection, users_collection, viewer_instances_collection
from config import INACTIVITY_THRESHOLD_HOURS

logger = logging.getLogger(__name__)

MONGO_VIEWER_TTL_HOURS = int(os.getenv("MONGO_VIEWER_TTL_HOURS", "48"))

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

async def cleanup_inactive_viewers():
    """Delete viewer resources that haven't been accessed in the threshold period"""
    threshold = datetime.utcnow() - timedelta(hours=MONGO_VIEWER_TTL_HOURS)

    stale_viewers = []
    async for viewer in viewer_instances_collection.find({"last_access": {"$lt": threshold}}):
        stale_viewers.append(viewer)

    logger.info(f"Found {len(stale_viewers)} stale mongo viewers to clean up")

    for viewer in stale_viewers:
        try:
            user_id = str(viewer["user_id"])
            await delete_mongo_viewer_resources(user_id)
            await viewer_instances_collection.delete_one({"_id": viewer["_id"]})
            logger.info(f"Cleaned up mongo viewer for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up mongo viewer for user {viewer.get('user_id')}: {e}")

async def run_cleanup_loop():
    """Run cleanup job periodically"""
    while True:
        try:
            await cleanup_inactive_apps()
            await cleanup_inactive_viewers()
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
        
        # Run every hour
        await asyncio.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_cleanup_loop())
