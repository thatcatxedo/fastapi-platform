"""
Lifespan module for FastAPI Platform
Handles application startup and shutdown lifecycle
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from database import client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed templates
    startup_logger = logging.getLogger("uvicorn")
    try:
        from seed_templates import seed_templates
        startup_logger.info("Starting template seeding...")
        await seed_templates(client)
        startup_logger.info("Template seeding completed on startup")
    except Exception as e:
        startup_logger.error(f"Warning: Template seeding failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    # Startup: migrate existing users to per-user MongoDB auth
    try:
        from migrate_mongo_users import migrate_existing_users
        startup_logger.info("Starting MongoDB user migration...")
        stats = await migrate_existing_users(client)
        startup_logger.info(f"MongoDB user migration completed: {stats['newly_migrated']} new, {stats['already_migrated']} existing, {stats['failed']} failed")
    except Exception as e:
        startup_logger.error(f"Warning: MongoDB user migration failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    # Startup: Set first user as admin if no admin exists
    try:
        from migrate_admin_role import migrate_admin_role
        startup_logger.info("Starting admin role migration...")
        await migrate_admin_role(client)
        startup_logger.info("Admin role migration completed")
    except Exception as e:
        startup_logger.error(f"Warning: Admin role migration failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    yield
    # Shutdown (if needed)
