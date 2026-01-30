"""
Database module for FastAPI Platform
Handles MongoDB client initialization and collection exports
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

# MongoDB client initialization
client = AsyncIOMotorClient(MONGO_URI)
db = client.fastapi_platform_db

# Collections
users_collection = db.users
apps_collection = db.apps
templates_collection = db.templates
viewer_instances_collection = db.viewer_instances
settings_collection = db.platform_settings
