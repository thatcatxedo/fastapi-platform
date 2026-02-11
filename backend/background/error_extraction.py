"""
Background job to extract 4xx/5xx errors from _platform_request_logs into app_errors.

Pulls failed requests from the runner middleware's request logs and writes to
app_errors_collection for the errors panel and dashboard.
"""
from datetime import datetime, timedelta, timezone
import asyncio
import logging

from database import (
    apps_collection,
    app_errors_collection,
    users_collection,
    client,
)
from mongo_users import get_mongo_db_name

logger = logging.getLogger(__name__)

# How often to run extraction (seconds)
EXTRACTION_INTERVAL = 300  # 5 minutes

# Look back window (seconds) - extract errors from this period
LOOKBACK_SECONDS = 3600  # 1 hour


async def extract_errors_for_app(app: dict) -> list:
    """
    Extract 4xx/5xx request logs for a single app into error documents.

    Returns list of documents to insert into app_errors_collection.
    """
    app_id = app.get("app_id")
    user_id = app.get("user_id")
    if not app_id or not user_id:
        return []

    database_id = app.get("database_id")
    if database_id is None:
        user = await users_collection.find_one({"_id": user_id}, {"default_database_id": 1})
        database_id = user.get("default_database_id", "default") if user else "default"

    db_name = get_mongo_db_name(str(user_id), database_id)
    since = datetime.now(timezone.utc) - timedelta(seconds=LOOKBACK_SECONDS)

    try:
        user_db = client[db_name]
        collection = user_db["_platform_request_logs"]

        errors = []
        async for doc in collection.find(
            {"app_id": app_id, "status_code": {"$gte": 400}, "timestamp": {"$gte": since}}
        ).sort("timestamp", -1):
            error_type = "server_error" if doc.get("status_code", 0) >= 500 else "client_error"
            errors.append({
                "app_id": app_id,
                "timestamp": doc["timestamp"],
                "status_code": doc.get("status_code", 0),
                "request_path": doc.get("path", ""),
                "request_method": doc.get("method", ""),
                "error_type": error_type,
            })

        return errors
    except Exception as e:
        logger.warning(f"Failed to extract errors for app {app_id}: {e}")
        return []


async def run_error_extraction():
    """Run one error extraction pass for all apps."""
    # Get existing error IDs to deduplicate (app_id, timestamp, path, status_code)
    existing = set()
    async for doc in app_errors_collection.find(
        {},
        {"app_id": 1, "timestamp": 1, "request_path": 1, "status_code": 1},
    ):
        key = (doc["app_id"], doc.get("timestamp"), doc.get("request_path", ""), doc.get("status_code"))
        existing.add(key)

    apps = []
    async for app in apps_collection.find(
        {"status": {"$ne": "deleted"}},
        {"app_id": 1, "user_id": 1, "database_id": 1},
    ):
        apps.append(app)

    if not apps:
        logger.debug("No apps to extract errors for")
        return

    logger.info(f"Extracting errors for {len(apps)} apps")

    to_insert = []
    for app in apps:
        errors = await extract_errors_for_app(app)
        for err in errors:
            key = (err["app_id"], err["timestamp"], err.get("request_path", ""), err.get("status_code"))
            if key not in existing:
                to_insert.append(err)
                existing.add(key)

    if to_insert:
        try:
            await app_errors_collection.insert_many(to_insert)
            logger.debug(f"Stored {len(to_insert)} error documents")
        except Exception as e:
            logger.error(f"Error storing errors: {e}")


async def run_error_extraction_loop():
    """Run error extraction periodically."""
    logger.info(f"Starting error extraction loop (interval: {EXTRACTION_INTERVAL}s)")

    while True:
        try:
            await run_error_extraction()
        except Exception as e:
            logger.error(f"Error in error extraction loop: {e}")

        await asyncio.sleep(EXTRACTION_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_error_extraction_loop())
