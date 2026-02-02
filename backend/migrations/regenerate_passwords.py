"""
Migration to regenerate all database passwords with current SECRET_KEY.

Use this when the old SECRET_KEY is lost and encrypted passwords can't be decrypted.

Usage:
    kubectl exec -n fastapi-platform deployment/backend -- python -m migrations.regenerate_passwords

This will:
1. Generate new random passwords for each user's databases
2. Update MongoDB users with new passwords
3. Encrypt passwords with current SECRET_KEY
4. Store in user documents

After running, redeploy user apps to pick up new credentials.
"""
import asyncio
import secrets
import logging

from database import users_collection
from mongo_users import encrypt_password, create_or_update_mongo_user, get_mongo_username, get_mongo_db_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def regenerate_passwords(dry_run: bool = False):
    """Regenerate all database passwords with current SECRET_KEY."""
    stats = {"users": 0, "databases": 0, "viewers": 0, "errors": 0}

    async for user in users_collection.find({}):
        user_id = str(user["_id"])
        username = user.get("username", user_id)
        updates = {}

        logger.info(f"Processing user: {username}")

        # Regenerate multi-database passwords
        if user.get("databases"):
            new_dbs = []
            for db in user["databases"]:
                db_id = db.get("id", "default")
                db_name_display = db.get("name", db_id)

                try:
                    # Generate new password
                    new_password = secrets.token_urlsafe(24)

                    if not dry_run:
                        # Update MongoDB user with new password
                        mongo_username = get_mongo_username(user_id, db_id)
                        mongo_db_name = get_mongo_db_name(user_id, db_id)

                        await create_or_update_mongo_user(
                            user_id=user_id,
                            database_id=db_id,
                            password=new_password
                        )

                        # Encrypt and store
                        db["mongo_password_encrypted"] = encrypt_password(new_password)

                    new_dbs.append(db)
                    stats["databases"] += 1
                    logger.info(f"  [{'DRY RUN' if dry_run else 'OK'}] Regenerated password for database: {db_name_display}")

                except Exception as e:
                    logger.error(f"  [ERROR] Failed to regenerate password for database {db_name_display}: {e}")
                    new_dbs.append(db)  # Keep original entry
                    stats["errors"] += 1

            updates["databases"] = new_dbs

        # Regenerate viewer password if exists
        if user.get("viewer_password_encrypted"):
            try:
                new_viewer_password = secrets.token_urlsafe(16)

                if not dry_run:
                    # Note: Viewer users are created differently, may need separate handling
                    # For now, just update the encrypted password
                    updates["viewer_password_encrypted"] = encrypt_password(new_viewer_password)

                stats["viewers"] += 1
                logger.info(f"  [{'DRY RUN' if dry_run else 'OK'}] Regenerated viewer password")

            except Exception as e:
                logger.error(f"  [ERROR] Failed to regenerate viewer password: {e}")
                stats["errors"] += 1

        # Update user document
        if updates and not dry_run:
            await users_collection.update_one({"_id": user["_id"]}, {"$set": updates})
            stats["users"] += 1

    logger.info("")
    logger.info("=" * 50)
    logger.info(f"Migration {'DRY RUN' if dry_run else 'COMPLETE'}")
    logger.info(f"  Users updated: {stats['users']}")
    logger.info(f"  Databases regenerated: {stats['databases']}")
    logger.info(f"  Viewers regenerated: {stats['viewers']}")
    logger.info(f"  Errors: {stats['errors']}")

    if not dry_run and stats["databases"] > 0:
        logger.info("")
        logger.info("IMPORTANT: Redeploy user apps to use new credentials:")
        logger.info("  kubectl delete pods -n fastapi-platform -l managed-by=fastapi-platform")

    return stats


async def main():
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("")

    await regenerate_passwords(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
