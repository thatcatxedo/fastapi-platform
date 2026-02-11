"""
Background job to aggregate request metrics from _platform_request_logs into app_metrics.

Reads from the runner middleware's request logs (stored in each user's MongoDB database)
and writes aggregated metrics to app_metrics_collection for the dashboard.
"""
from datetime import datetime, timedelta, timezone
import asyncio
import logging

from database import (
    apps_collection,
    app_metrics_collection,
    users_collection,
    client,
)
from mongo_users import get_mongo_db_name

logger = logging.getLogger(__name__)

# How often to run aggregation (seconds)
AGGREGATION_INTERVAL = 300  # 5 minutes

# Time window to aggregate (seconds)
AGGREGATION_WINDOW_SECONDS = 3600  # 1 hour


async def aggregate_metrics_for_app(app: dict) -> dict | None:
    """
    Aggregate request logs for a single app into metrics.

    Returns a document to insert into app_metrics_collection, or None on error.
    """
    app_id = app.get("app_id")
    user_id = app.get("user_id")
    if not app_id or not user_id:
        return None

    # Resolve database_id: from app, or user's default
    database_id = app.get("database_id")
    if database_id is None:
        user = await users_collection.find_one({"_id": user_id}, {"default_database_id": 1})
        database_id = user.get("default_database_id", "default") if user else "default"

    db_name = get_mongo_db_name(str(user_id), database_id)
    since = datetime.now(timezone.utc) - timedelta(seconds=AGGREGATION_WINDOW_SECONDS)

    try:
        user_db = client[db_name]
        collection = user_db["_platform_request_logs"]

        pipeline = [
            {"$match": {"app_id": app_id, "timestamp": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "request_count": {"$sum": 1},
                "error_count": {"$sum": {"$cond": [{"$gte": ["$status_code", 400]}, 1, 0]}},
                "avg_response_time_ms": {"$avg": "$duration_ms"},
                "min_response_time_ms": {"$min": "$duration_ms"},
                "max_response_time_ms": {"$max": "$duration_ms"},
            }},
        ]

        result = await collection.aggregate(pipeline).to_list(1)
        if not result or result[0].get("_id") is None:
            # No requests in window - optionally skip or write zeros
            return None

        data = result[0]
        return {
            "app_id": app_id,
            "timestamp": datetime.now(timezone.utc),
            "request_count": data.get("request_count", 0),
            "error_count": data.get("error_count", 0),
            "avg_response_time_ms": round(data.get("avg_response_time_ms", 0) or 0, 2),
            "min_response_time_ms": round(data.get("min_response_time_ms", 0) or 0, 2),
            "max_response_time_ms": round(data.get("max_response_time_ms", 0) or 0, 2),
        }
    except Exception as e:
        logger.warning(f"Failed to aggregate metrics for app {app_id}: {e}")
        return None


async def run_metrics_aggregation():
    """Run one metrics aggregation pass for all apps."""
    apps = []
    async for app in apps_collection.find(
        {"status": {"$ne": "deleted"}},
        {"app_id": 1, "user_id": 1, "database_id": 1},
    ):
        apps.append(app)

    if not apps:
        logger.debug("No apps to aggregate metrics for")
        return

    logger.info(f"Aggregating metrics for {len(apps)} apps")

    metrics_docs = []
    for app in apps:
        doc = await aggregate_metrics_for_app(app)
        if doc and doc.get("request_count", 0) > 0:
            metrics_docs.append(doc)

    if metrics_docs:
        try:
            await app_metrics_collection.insert_many(metrics_docs)
            logger.debug(f"Stored {len(metrics_docs)} metrics documents")
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")


async def run_metrics_aggregation_loop():
    """Run metrics aggregation periodically."""
    logger.info(f"Starting metrics aggregation loop (interval: {AGGREGATION_INTERVAL}s)")

    while True:
        try:
            await run_metrics_aggregation()
        except Exception as e:
            logger.error(f"Error in metrics aggregation loop: {e}")

        await asyncio.sleep(AGGREGATION_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_metrics_aggregation_loop())
