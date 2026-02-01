"""
Database module for FastAPI Platform
Handles MongoDB client initialization and collection exports
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

logger = logging.getLogger(__name__)

# MongoDB client initialization
client = AsyncIOMotorClient(MONGO_URI)
db = client.fastapi_platform_db

# Collections
users_collection = db.users
apps_collection = db.apps
templates_collection = db.templates
viewer_instances_collection = db.viewer_instances
settings_collection = db.platform_settings

# Observability collections (Phase 1e)
app_metrics_collection = db.app_metrics
app_errors_collection = db.app_errors
app_health_checks_collection = db.app_health_checks

# Chat collections
conversations_collection = db.conversations
messages_collection = db.messages


async def setup_ttl_indexes():
    """
    Set up TTL indexes for observability collections.
    Documents expire after 24 hours (86400 seconds).
    """
    try:
        # TTL index on app_metrics - expire after 24 hours
        await app_metrics_collection.create_index(
            "timestamp",
            expireAfterSeconds=86400,
            background=True
        )
        logger.info("Created TTL index on app_metrics.timestamp")
        
        # TTL index on app_errors - expire after 24 hours
        await app_errors_collection.create_index(
            "timestamp",
            expireAfterSeconds=86400,
            background=True
        )
        logger.info("Created TTL index on app_errors.timestamp")
        
        # TTL index on app_health_checks - expire after 24 hours
        await app_health_checks_collection.create_index(
            "timestamp",
            expireAfterSeconds=86400,
            background=True
        )
        logger.info("Created TTL index on app_health_checks.timestamp")
        
        # Create regular indexes for efficient queries
        await app_metrics_collection.create_index("app_id", background=True)
        await app_errors_collection.create_index("app_id", background=True)
        await app_health_checks_collection.create_index("app_id", background=True)
        
        # Compound index for recent health checks per app
        await app_health_checks_collection.create_index(
            [("app_id", 1), ("timestamp", -1)],
            background=True
        )
        
        logger.info("Observability TTL indexes setup complete")
    except Exception as e:
        logger.error(f"Error setting up TTL indexes: {e}")
