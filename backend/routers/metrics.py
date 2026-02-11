"""
Metrics and observability routes for FastAPI Platform.

This module contains thin HTTP handlers that delegate to MetricsService
for all business logic.
"""
from fastapi import APIRouter, Depends
import logging

from models import (
    AppMetricsResponse, AppErrorsResponse, AppHealthStatusResponse,
    AppRequestLogsResponse
)
from auth import get_current_user
from services.app_service import app_service
from services.metrics_service import metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["metrics"])


@router.get("/{app_id}/metrics", response_model=AppMetricsResponse)
async def get_app_metrics(app_id: str, hours: int = 24, user: dict = Depends(get_current_user)):
    """Get aggregated metrics for an app over the specified time period."""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    return await metrics_service.get_app_metrics(app_id, hours)


@router.get("/{app_id}/errors", response_model=AppErrorsResponse)
async def get_app_errors(app_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    """Get recent errors for an app."""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    return await metrics_service.get_app_errors(app_id, limit)


@router.get("/{app_id}/health-status", response_model=AppHealthStatusResponse)
async def get_app_health_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get health status for an app based on recent health checks."""
    await app_service.get_by_app_id(app_id, user)  # Verify app exists and user owns it
    return await metrics_service.get_health_status(app_id)


@router.get("/{app_id}/requests", response_model=AppRequestLogsResponse)
async def get_app_requests(
    app_id: str, limit: int = 50, user: dict = Depends(get_current_user)
):
    """Get recent HTTP request logs for an app.

    Request logs are captured by middleware running inside the app's runner
    container and stored in the user's MongoDB database.
    """
    app = await app_service.get_by_app_id(app_id, user)
    return await metrics_service.get_request_logs(app_id, app, user, limit)


# Re-export for backwards compatibility
async def get_metrics_summary(app_id: str) -> dict:
    """
    Helper function to get a metrics summary for an app.
    Used by the apps list endpoint to include metrics in dashboard.
    """
    return await metrics_service.get_summary(app_id)
