"""
Metrics service for FastAPI Platform.

This service handles app metrics aggregation, error tracking, and health status.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from models import (
    AppMetricsResponse, AppErrorsResponse, AppErrorEntry,
    AppHealthStatusResponse, HealthStatus,
    AppRequestLogsResponse, RequestLogEntry
)

logger = logging.getLogger(__name__)


class MetricsServiceError(Exception):
    """Base exception for metrics service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class MetricsService:
    """Service for app metrics, errors, and health status."""

    def __init__(
        self,
        metrics_collection=None,
        errors_collection=None,
        health_checks_collection=None,
        mongo_client=None
    ):
        """
        Initialize MetricsService with optional dependency injection.
        """
        if metrics_collection is None:
            from database import (
                app_metrics_collection,
                app_errors_collection,
                app_health_checks_collection,
                client as default_client
            )
            self.metrics = app_metrics_collection
            self.errors = errors_collection or app_errors_collection
            self.health_checks = health_checks_collection or app_health_checks_collection
            self.client = mongo_client or default_client
        else:
            self.metrics = metrics_collection
            self.errors = errors_collection
            self.health_checks = health_checks_collection
            self.client = mongo_client

    # =========================================================================
    # Metrics
    # =========================================================================

    async def get_app_metrics(self, app_id: str, hours: int = 24) -> AppMetricsResponse:
        """
        Get aggregated metrics for an app over the specified time period.

        Args:
            app_id: App identifier
            hours: Number of hours to aggregate (default 24)

        Returns:
            AppMetricsResponse with aggregated metrics
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        pipeline = [
            {"$match": {"app_id": app_id, "timestamp": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total_requests": {"$sum": "$request_count"},
                "total_errors": {"$sum": "$error_count"},
                "avg_response_time": {"$avg": "$avg_response_time_ms"},
                "min_response_time": {"$min": "$min_response_time_ms"},
                "max_response_time": {"$max": "$max_response_time_ms"}
            }}
        ]

        result = await self.metrics.aggregate(pipeline).to_list(1)

        if result:
            data = result[0]
            return AppMetricsResponse(
                app_id=app_id,
                request_count=data.get("total_requests", 0) or 0,
                error_count=data.get("total_errors", 0) or 0,
                avg_response_time_ms=round(data.get("avg_response_time", 0) or 0, 2),
                min_response_time_ms=round(data.get("min_response_time", 0) or 0, 2),
                max_response_time_ms=round(data.get("max_response_time", 0) or 0, 2),
                period_hours=hours
            )

        return AppMetricsResponse(app_id=app_id, period_hours=hours)

    # =========================================================================
    # Errors
    # =========================================================================

    async def get_app_errors(self, app_id: str, limit: int = 50) -> AppErrorsResponse:
        """
        Get recent errors for an app.

        Args:
            app_id: App identifier
            limit: Maximum number of errors to return (default 50)

        Returns:
            AppErrorsResponse with error entries and total count
        """
        errors = []
        async for error in self.errors.find(
            {"app_id": app_id}
        ).sort("timestamp", -1).limit(limit):
            errors.append(AppErrorEntry(
                timestamp=error["timestamp"].isoformat() if error.get("timestamp") else "",
                status_code=error.get("status_code", 0),
                request_path=error.get("request_path"),
                request_method=error.get("request_method"),
                error_type=error.get("error_type", "unknown")
            ))

        total_count = await self.errors.count_documents({"app_id": app_id})

        return AppErrorsResponse(
            app_id=app_id,
            errors=errors,
            total_count=total_count
        )

    # =========================================================================
    # Health Status
    # =========================================================================

    async def get_health_status(self, app_id: str) -> AppHealthStatusResponse:
        """
        Get health status for an app based on recent health checks.

        Args:
            app_id: App identifier

        Returns:
            AppHealthStatusResponse with health status details
        """
        since = datetime.utcnow() - timedelta(minutes=5)

        checks = []
        async for check in self.health_checks.find(
            {"app_id": app_id, "timestamp": {"$gte": since}}
        ).sort("timestamp", -1):
            checks.append(check)

        if not checks:
            # No recent checks - unknown status
            return AppHealthStatusResponse(
                app_id=app_id,
                health=HealthStatus(
                    status="unknown",
                    last_check=None,
                    response_time_ms=None,
                    checks_passed=0,
                    checks_failed=0,
                    uptime_percent=None
                )
            )

        # Calculate health status
        healthy_checks = sum(1 for c in checks if c.get("status") == "healthy")
        failed_checks = len(checks) - healthy_checks

        # Determine status
        if failed_checks == 0:
            status = "healthy"
        elif healthy_checks == 0:
            status = "unhealthy"
        else:
            status = "degraded"

        # Get most recent check
        latest = checks[0]

        # Calculate uptime percentage
        uptime_percent = (healthy_checks / len(checks)) * 100 if checks else None

        return AppHealthStatusResponse(
            app_id=app_id,
            health=HealthStatus(
                status=status,
                last_check=latest["timestamp"].isoformat() if latest.get("timestamp") else None,
                response_time_ms=latest.get("response_time_ms"),
                checks_passed=healthy_checks,
                checks_failed=failed_checks,
                uptime_percent=round(uptime_percent, 1) if uptime_percent is not None else None
            )
        )

    # =========================================================================
    # Summary (for dashboard)
    # =========================================================================

    async def get_summary(self, app_id: str) -> dict:
        """
        Get a metrics summary for an app.
        Used by the apps list endpoint to include metrics in dashboard.

        Args:
            app_id: App identifier

        Returns:
            Dict with request_count, error_count, avg_response_time_ms, health_status
        """
        since = datetime.utcnow() - timedelta(hours=24)

        # Get aggregated metrics
        pipeline = [
            {"$match": {"app_id": app_id, "timestamp": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total_requests": {"$sum": "$request_count"},
                "total_errors": {"$sum": "$error_count"},
                "avg_response_time": {"$avg": "$avg_response_time_ms"}
            }}
        ]

        metrics_result = await self.metrics.aggregate(pipeline).to_list(1)

        # Get health status
        health_since = datetime.utcnow() - timedelta(minutes=5)
        health_checks = await self.health_checks.find(
            {"app_id": app_id, "timestamp": {"$gte": health_since}}
        ).to_list(10)

        # Determine health status
        if not health_checks:
            health_status = "unknown"
        else:
            healthy = sum(1 for c in health_checks if c.get("status") == "healthy")
            if healthy == len(health_checks):
                health_status = "healthy"
            elif healthy == 0:
                health_status = "unhealthy"
            else:
                health_status = "degraded"

        metrics_data = metrics_result[0] if metrics_result else {}

        return {
            "request_count": metrics_data.get("total_requests", 0) or 0,
            "error_count": metrics_data.get("total_errors", 0) or 0,
            "avg_response_time_ms": round(metrics_data.get("avg_response_time", 0) or 0, 2),
            "health_status": health_status
        }


    # =========================================================================
    # Request Logs (from runner middleware, stored in user databases)
    # =========================================================================

    async def get_request_logs(
        self, app_id: str, app: dict, user: dict, limit: int = 50
    ) -> AppRequestLogsResponse:
        """
        Get recent request logs for an app from the user's database.

        The runner middleware writes request logs to _platform_request_logs
        in the user's own MongoDB database.
        """
        from mongo_users import get_mongo_db_name

        user_id = str(user["_id"])
        database_id = app.get("database_id") or user.get("default_database_id", "default")
        db_name = get_mongo_db_name(user_id, database_id)

        try:
            user_db = self.client[db_name]
            collection = user_db["_platform_request_logs"]

            requests = []
            async for doc in collection.find(
                {"app_id": app_id}
            ).sort("timestamp", -1).limit(limit):
                requests.append(RequestLogEntry(
                    timestamp=doc["timestamp"].isoformat() if doc.get("timestamp") else "",
                    method=doc.get("method", ""),
                    path=doc.get("path", ""),
                    status_code=doc.get("status_code", 0),
                    duration_ms=doc.get("duration_ms", 0),
                    query_string=doc.get("query_string", ""),
                ))

            total_count = await collection.count_documents({"app_id": app_id})

            return AppRequestLogsResponse(
                app_id=app_id,
                requests=requests,
                total_count=total_count
            )
        except Exception as e:
            logger.warning(f"Failed to get request logs for app {app_id}: {e}")
            return AppRequestLogsResponse(
                app_id=app_id,
                requests=[],
                total_count=0
            )


# Singleton instance for production use
metrics_service = MetricsService()
