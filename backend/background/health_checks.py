"""
Background job to poll health endpoints for user apps
"""
from datetime import datetime
import asyncio
import logging
import aiohttp
from database import apps_collection, app_health_checks_collection
from config import APP_DOMAIN

logger = logging.getLogger(__name__)

# Health check interval in seconds
HEALTH_CHECK_INTERVAL = 60

# Timeout for health check requests
HEALTH_CHECK_TIMEOUT = 10


async def check_app_health(app: dict) -> dict:
    """
    Check the health of a single app by calling its /health endpoint.
    Returns a health check result document.
    """
    app_id = app["app_id"]
    health_url = f"https://app-{app_id}.{APP_DOMAIN}/health"

    result = {
        "app_id": app_id,
        "timestamp": datetime.utcnow(),
        "status": "unknown",
        "response_time_ms": None,
        "error": None
    }

    try:
        start_time = asyncio.get_event_loop().time()

        timeout = aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(health_url, ssl=False) as response:
                end_time = asyncio.get_event_loop().time()
                response_time_ms = (end_time - start_time) * 1000

                result["response_time_ms"] = round(response_time_ms, 2)

                if response.status == 200:
                    result["status"] = "healthy"
                else:
                    result["status"] = "unhealthy"
                    result["error"] = f"HTTP {response.status}"

    except asyncio.TimeoutError:
        result["status"] = "timeout"
        result["error"] = "Health check timed out"
    except aiohttp.ClientError as e:
        result["status"] = "unhealthy"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Unexpected error checking health for app {app_id}: {e}")

    return result


async def poll_all_apps():
    """
    Poll health endpoints for all running apps.
    """
    # Find all running apps
    running_apps = []
    async for app in apps_collection.find({"status": "running"}):
        running_apps.append(app)

    if not running_apps:
        logger.debug("No running apps to health check")
        return

    logger.info(f"Health checking {len(running_apps)} running apps")

    # Check health of all apps concurrently (with some limit)
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent health checks

    async def check_with_semaphore(app):
        async with semaphore:
            return await check_app_health(app)

    results = await asyncio.gather(
        *[check_with_semaphore(app) for app in running_apps],
        return_exceptions=True
    )

    # Store results in database
    health_checks = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Health check task error: {result}")
            continue
        health_checks.append(result)

    if health_checks:
        try:
            await app_health_checks_collection.insert_many(health_checks)
            logger.debug(f"Stored {len(health_checks)} health check results")
        except Exception as e:
            logger.error(f"Error storing health check results: {e}")

    # Log summary
    healthy = sum(1 for r in health_checks if r.get("status") == "healthy")
    unhealthy = len(health_checks) - healthy
    logger.info(f"Health check complete: {healthy} healthy, {unhealthy} unhealthy/unknown")


async def run_health_check_loop():
    """Run health check polling periodically"""
    logger.info(f"Starting health check loop (interval: {HEALTH_CHECK_INTERVAL}s)")

    while True:
        try:
            await poll_all_apps()
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_health_check_loop())
