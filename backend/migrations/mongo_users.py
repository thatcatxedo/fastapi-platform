"""
Migration script for creating MongoDB users for existing platform users.

This script should be run once to migrate existing users to the new
per-user MongoDB authentication system. It can also be run on startup
to ensure all users have MongoDB credentials.

Usage:
    # Run manually
    python -m migrations.mongo_users

    # Or import and call from lifespan
    from migrations.mongo_users import migrate_existing_users
    await migrate_existing_users(client)
"""
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from mongo_users import (
    create_mongo_user,
    encrypt_password,
    verify_mongo_user_exists
)

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


async def migrate_existing_users(client: AsyncIOMotorClient = None) -> dict:
    """
    Create MongoDB users for all existing platform users who don't have credentials.

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
        "already_migrated": 0,
        "newly_migrated": 0,
        "failed": 0,
        "errors": []
    }

    # Find all users without MongoDB credentials
    async for user in users_collection.find({}):
        stats["total_users"] += 1
        user_id = str(user["_id"])
        username = user.get("username", "unknown")

        # Check if already has MongoDB credentials
        if user.get("mongo_password_encrypted"):
            # Verify the MongoDB user actually exists
            if await verify_mongo_user_exists(client, user_id):
                stats["already_migrated"] += 1
                logger.debug(f"User {username} ({user_id}) already migrated")
                continue
            else:
                logger.warning(f"User {username} ({user_id}) has credentials but MongoDB user missing, recreating")

        # Create MongoDB user
        try:
            mongo_username, mongo_password = await create_mongo_user(client, user_id)

            # Store encrypted password in user document
            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"mongo_password_encrypted": encrypt_password(mongo_password)}}
            )

            stats["newly_migrated"] += 1
            logger.info(f"Migrated user {username} ({user_id}) - created MongoDB user {mongo_username}")

        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Failed to migrate user {username} ({user_id}): {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)

    return stats


async def main():
    """Run migration as standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting MongoDB user migration...")

    client = AsyncIOMotorClient(MONGO_URI)

    try:
        # Test connection
        await client.admin.command("ping")
        logger.info("Connected to MongoDB")

        # Run migration
        stats = await migrate_existing_users(client)

        # Print summary
        logger.info("=" * 50)
        logger.info("Migration Complete")
        logger.info("=" * 50)
        logger.info(f"Total users:      {stats['total_users']}")
        logger.info(f"Already migrated: {stats['already_migrated']}")
        logger.info(f"Newly migrated:   {stats['newly_migrated']}")
        logger.info(f"Failed:           {stats['failed']}")

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
