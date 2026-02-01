"""
Migration script for creating viewer MongoDB users for existing platform users.

This script creates viewer users with access to all databases for users who
don't have viewer credentials yet.

Usage:
    # Run manually
    python -m migrations.viewer_users

    # Or import and call from lifespan
    from migrations.viewer_users import migrate_viewer_users
    await migrate_viewer_users(client)
"""
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from mongo_users import (
    create_viewer_user,
    encrypt_password,
    get_viewer_username
)

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


async def migrate_viewer_users(client: AsyncIOMotorClient = None) -> dict:
    """
    Create viewer MongoDB users for all existing platform users who don't have one.

    Args:
        client: Optional MongoDB client (creates new one if None)

    Returns:
        dict with migration statistics
    """
    if client is None:
        client = AsyncIOMotorClient(MONGO_URI)

    db = client.fastapi_platform_db
    users_collection = db.users

    stats = {
        "total_users": 0,
        "already_has_viewer": 0,
        "created_viewer": 0,
        "skipped_no_databases": 0,
        "failed": 0,
        "errors": []
    }

    # Find all users
    async for user in users_collection.find({}):
        stats["total_users"] += 1
        user_id = str(user["_id"])
        username = user.get("username", "unknown")

        # Check if already has viewer credentials
        if user.get("viewer_password_encrypted"):
            stats["already_has_viewer"] += 1
            logger.debug(f"User {username} ({user_id}) already has viewer user")
            continue

        # Get user's database IDs
        databases = user.get("databases", [])
        if not databases:
            stats["skipped_no_databases"] += 1
            logger.debug(f"User {username} ({user_id}) has no databases, skipping")
            continue

        database_ids = [db["id"] for db in databases]

        # Create viewer user
        try:
            viewer_password = await create_viewer_user(client, user_id, database_ids)

            # Store encrypted password in user document
            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"viewer_password_encrypted": encrypt_password(viewer_password)}}
            )

            stats["created_viewer"] += 1
            viewer_username = get_viewer_username(user_id)
            logger.info(f"Created viewer user {viewer_username} for {username} ({user_id}) with access to {len(database_ids)} databases")

        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Failed to create viewer user for {username} ({user_id}): {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)

    return stats


async def main():
    """Run migration as standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting viewer user migration...")

    client = AsyncIOMotorClient(MONGO_URI)

    try:
        # Test connection
        await client.admin.command("ping")
        logger.info("Connected to MongoDB")

        # Run migration
        stats = await migrate_viewer_users(client)

        # Print summary
        logger.info("=" * 50)
        logger.info("Viewer User Migration Complete")
        logger.info("=" * 50)
        logger.info(f"Total users:          {stats['total_users']}")
        logger.info(f"Already has viewer:   {stats['already_has_viewer']}")
        logger.info(f"Created viewer:       {stats['created_viewer']}")
        logger.info(f"Skipped (no dbs):     {stats['skipped_no_databases']}")
        logger.info(f"Failed:               {stats['failed']}")

        if stats["errors"]:
            logger.error("Errors encountered:")
            for error in stats["errors"]:
                logger.error(f"  - {error}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
