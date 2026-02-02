"""
Metrics and observability routes for FastAPI Platform
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import logging

from models import (
    AppMetricsResponse, AppErrorsResponse, AppErrorEntry,
    AppHealthStatusResponse, HealthStatus
)
from auth import get_current_user
from database import app_metrics_collection, app_errors_collection, app_health_checks_collection
from services.app_service import app_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["metrics"])


@router.get("/{app_id}/metrics", response_model=AppMetricsResponse)
async def get_app_metrics(app_id: str, hours: int = 24, user: dict = Depends(get_current_user)):
    """Get aggregated metrics for an app over the specified time period"""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    
    # Calculate time window
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Aggregate metrics from the time window
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
    
    result = await app_metrics_collection.aggregate(pipeline).to_list(1)
    
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


@router.get("/{app_id}/errors", response_model=AppErrorsResponse)
async def get_app_errors(app_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Get recent errors for an app"""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    
    # Fetch recent errors, sorted by timestamp descending
    errors = []
    async for error in app_errors_collection.find(
        {"app_id": app_id}
    ).sort("timestamp", -1).limit(limit):
        errors.append(AppErrorEntry(
            timestamp=error["timestamp"].isoformat() if error.get("timestamp") else "",
            status_code=error.get("status_code", 0),
            request_path=error.get("request_path"),
            request_method=error.get("request_method"),
            error_type=error.get("error_type", "unknown")
        ))
    
    # Get total count
    total_count = await app_errors_collection.count_documents({"app_id": app_id})
    
    return AppErrorsResponse(
        app_id=app_id,
        errors=errors,
        total_count=total_count
    )


@router.get("/{app_id}/health-status", response_model=AppHealthStatusResponse)
async def get_app_health_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get health status for an app based on recent health checks"""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    
    # Get health checks from the last 5 minutes
    since = datetime.utcnow() - timedelta(minutes=5)
    
    checks = []
    async for check in app_health_checks_collection.find(
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


async def get_metrics_summary(app_id: str) -> dict:
    """
    Helper function to get a metrics summary for an app.
    Used by the apps list endpoint to include metrics in dashboard.
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
    
    metrics_result = await app_metrics_collection.aggregate(pipeline).to_list(1)
    
    # Get health status
    health_since = datetime.utcnow() - timedelta(minutes=5)
    health_checks = await app_health_checks_collection.find(
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
