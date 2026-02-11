"""
Lifespan module for FastAPI Platform
Handles application startup and shutdown lifecycle
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
import logging

from database import client, setup_ttl_indexes

logger = logging.getLogger(__name__)

# Track background tasks for cleanup on shutdown
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_logger = logging.getLogger("uvicorn")
    
    # Startup: seed templates
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
        from migrations.mongo_users import migrate_existing_users
        startup_logger.info("Starting MongoDB user migration...")
        stats = await migrate_existing_users(client)
        startup_logger.info(f"MongoDB user migration completed: {stats['newly_migrated']} new, {stats['already_migrated']} existing, {stats['failed']} failed")
    except Exception as e:
        startup_logger.error(f"Warning: MongoDB user migration failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())

    # Startup: migrate viewer users for all-database access
    try:
        from migrations.viewer_users import migrate_viewer_users
        startup_logger.info("Starting viewer user migration...")
        stats = await migrate_viewer_users(client)
        startup_logger.info(f"Viewer user migration completed: {stats['created_viewer']} new, {stats['already_has_viewer']} existing, {stats['failed']} failed")
    except Exception as e:
        startup_logger.error(f"Warning: Viewer user migration failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    # Startup: Set first user as admin if no admin exists
    try:
        from migrations.admin_role import migrate_admin_role
        startup_logger.info("Starting admin role migration...")
        await migrate_admin_role(client)
        startup_logger.info("Admin role migration completed")
    except Exception as e:
        startup_logger.error(f"Warning: Admin role migration failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    # Startup: Setup TTL indexes for observability collections
    try:
        startup_logger.info("Setting up TTL indexes...")
        await setup_ttl_indexes()
        startup_logger.info("TTL indexes setup completed")
    except Exception as e:
        startup_logger.error(f"Warning: TTL index setup failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    # Startup: Start background tasks
    try:
        from background.cleanup import run_cleanup_loop
        from background.health_checks import run_health_check_loop
        from background.metrics_aggregation import run_metrics_aggregation_loop
        from background.error_extraction import run_error_extraction_loop
        from log_parser import run_log_parser_loop
        
        startup_logger.info("Starting background tasks...")
        
        cleanup_task = asyncio.create_task(run_cleanup_loop())
        background_tasks.append(cleanup_task)
        startup_logger.info("Cleanup task started")
        
        health_task = asyncio.create_task(run_health_check_loop())
        background_tasks.append(health_task)
        startup_logger.info("Health check task started")
        
        metrics_task = asyncio.create_task(run_metrics_aggregation_loop())
        background_tasks.append(metrics_task)
        startup_logger.info("Metrics aggregation task started")
        
        errors_task = asyncio.create_task(run_error_extraction_loop())
        background_tasks.append(errors_task)
        startup_logger.info("Error extraction task started")
        
        log_parser_task = asyncio.create_task(run_log_parser_loop())
        background_tasks.append(log_parser_task)
        startup_logger.info("Log parser task started")
        
    except Exception as e:
        startup_logger.error(f"Warning: Background task startup failed: {e}")
        import traceback
        startup_logger.error(traceback.format_exc())
    
    yield
    
    # Shutdown: Cancel background tasks
    shutdown_logger = logging.getLogger("uvicorn")
    shutdown_logger.info("Shutting down background tasks...")
    
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    shutdown_logger.info("Background tasks shutdown complete")
