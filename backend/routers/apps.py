"""
App management routes for FastAPI Platform.

This module contains thin HTTP handlers that delegate to AppService
for all business logic.
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional
import asyncio
import logging

from models import (
    AppCreate, AppUpdate, AppResponse, AppDetailResponse, AppStatusResponse,
    AppDeployStatusResponse, ValidateRequest, AppLogsResponse, AppEventsResponse,
    LogLine, K8sEvent, DraftUpdate, VersionEntry, VersionHistoryResponse
)
from auth import get_current_user
from utils import error_payload
from services.app_service import (
    app_service,
    AppServiceError,
    AppNotFoundError,
    ValidationError,
    InvalidRequestError,
    InvalidDatabaseError,
    DeploymentError,
    InvalidVersionError
)
from deployment import get_deployment_status, get_pod_logs, get_app_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["apps"])


def handle_service_error(e: AppServiceError) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    status_map = {
        "NOT_FOUND": 404,
        "VALIDATION_FAILED": 400,
        "INVALID_REQUEST": 400,
        "INVALID_DATABASE": 400,
        "DEPLOY_FAILED": 500,
        "INVALID_VERSION": 400,
    }
    status_code = status_map.get(e.code, 500)
    return HTTPException(
        status_code=status_code,
        detail=error_payload(e.code, e.message, e.details if e.details else None)
    )


# =============================================================================
# List and Create
# =============================================================================

@router.get("", response_model=List[AppResponse])
async def list_apps(user: dict = Depends(get_current_user)):
    """List all apps for the current user."""
    apps = await app_service.list_for_user(user)
    return [app_service.to_response(app) for app in apps]


@router.post("", response_model=AppResponse)
async def create_app(app_data: AppCreate, user: dict = Depends(get_current_user)):
    """Create a new app with validation and deployment."""
    try:
        app = await app_service.create(app_data, user)
        return app_service.to_response(app)
    except AppServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Get, Update, Delete
# =============================================================================

@router.get("/{app_id}", response_model=AppDetailResponse)
async def get_app(app_id: str, user: dict = Depends(get_current_user)):
    """Get detailed information about an app."""
    try:
        app, has_unpublished_changes = await app_service.get_with_changes_flag(app_id, user)
        return app_service.to_detail_response(app, has_unpublished_changes)
    except AppServiceError as e:
        raise handle_service_error(e)


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(app_id: str, app_data: AppUpdate, user: dict = Depends(get_current_user)):
    """Update an existing app."""
    try:
        app = await app_service.update(app_id, app_data, user)
        return app_service.to_response(app)
    except AppServiceError as e:
        raise handle_service_error(e)


@router.delete("/{app_id}")
async def delete_app(app_id: str, user: dict = Depends(get_current_user)):
    """Delete an app."""
    try:
        await app_service.delete(app_id, user)
        return {"success": True, "message": "App deleted"}
    except AppServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Clone and Draft
# =============================================================================

@router.post("/{app_id}/clone", response_model=AppResponse)
async def clone_app(app_id: str, user: dict = Depends(get_current_user)):
    """Clone an existing app - copies code/files and env var keys (not values)."""
    try:
        app = await app_service.clone(app_id, user)
        return app_service.to_response(app)
    except AppServiceError as e:
        raise handle_service_error(e)


@router.put("/{app_id}/draft", response_model=AppDetailResponse)
async def save_draft(app_id: str, draft: DraftUpdate, user: dict = Depends(get_current_user)):
    """Save draft code/files without deploying."""
    try:
        app, has_unpublished_changes = await app_service.save_draft(app_id, draft, user)
        return app_service.to_detail_response(app, has_unpublished_changes)
    except AppServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Status and Deployment
# =============================================================================

@router.get("/{app_id}/status", response_model=AppStatusResponse)
async def get_app_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get deployment status for an app."""
    try:
        app = await app_service.get_by_app_id(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    pod_status = None
    deployment_ready = False

    try:
        k8s_status = await get_deployment_status(app, user)
        if k8s_status:
            pod_status = k8s_status.get("pod_status")
            deployment_ready = k8s_status.get("ready", False)
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")

    return AppStatusResponse(
        status=app["status"],
        pod_status=pod_status,
        error_message=app.get("error_message"),
        deployment_ready=deployment_ready,
        deploy_stage=app.get("deploy_stage"),
        last_error=app.get("last_error")
    )


@router.get("/{app_id}/deploy-status", response_model=AppDeployStatusResponse)
async def get_app_deploy_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get detailed deployment status for an app."""
    try:
        app = await app_service.get_by_app_id(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    pod_status = None
    deployment_ready = False

    try:
        k8s_status = await get_deployment_status(app, user)
        if k8s_status:
            pod_status = k8s_status.get("pod_status")
            deployment_ready = k8s_status.get("ready", False)
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")

    return AppDeployStatusResponse(
        status=app.get("status", "unknown"),
        deploy_stage=app.get("deploy_stage"),
        deployment_ready=deployment_ready,
        pod_status=pod_status,
        last_error=app.get("last_error"),
        last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None
    )


# =============================================================================
# Validation
# =============================================================================

@router.post("/validate")
async def validate_app_code(payload: ValidateRequest, user: dict = Depends(get_current_user)):
    """Validate code/files before creating an app."""
    from validation import validate_code, validate_multifile

    allowed_imports = await app_service.get_allowed_imports()

    if payload.files:
        entrypoint = payload.entrypoint or "app.py"
        is_valid, error_msg, error_line, error_file = validate_multifile(
            payload.files, entrypoint, allowed_imports_override=allowed_imports
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": error_file}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    elif payload.code:
        is_valid, error_msg, error_line = validate_code(
            payload.code, allowed_imports_override=allowed_imports
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": None}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    else:
        return {"valid": False, "message": "No code or files provided", "line": None, "file": None}


@router.post("/{app_id}/validate")
async def validate_existing_app(app_id: str, payload: ValidateRequest, user: dict = Depends(get_current_user)):
    """Validate code/files for an existing app."""
    from validation import validate_code, validate_multifile

    try:
        app = await app_service.get_by_app_id(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    mode = app.get("mode", "single")
    allowed_imports = await app_service.get_allowed_imports()

    if mode == "multi" or payload.files:
        # Merge payload files with existing files to allow partial updates
        existing_files = app.get("files", {})
        if payload.files:
            files = {**existing_files, **payload.files}
        else:
            files = existing_files
        entrypoint = payload.entrypoint or app.get("entrypoint", "app.py")
        is_valid, error_msg, error_line, error_file = validate_multifile(
            files, entrypoint, allowed_imports_override=allowed_imports
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": error_file}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    else:
        code = payload.code or app.get("code", "")
        is_valid, error_msg, error_line = validate_code(
            code, allowed_imports_override=allowed_imports
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": None}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}


# =============================================================================
# Activity
# =============================================================================

@router.post("/{app_id}/activity")
async def record_activity(app_id: str, user: dict = Depends(get_current_user)):
    """Record activity timestamp for an app."""
    try:
        await app_service.record_activity(app_id, user)
        return {"success": True}
    except AppServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Logs and Events
# =============================================================================

@router.get("/{app_id}/logs", response_model=AppLogsResponse)
async def get_app_logs(
    app_id: str,
    tail_lines: int = 100,
    since_seconds: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """Get live pod logs for an app."""
    try:
        await app_service.get_by_app_id(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    result = await get_pod_logs(app_id, tail_lines, since_seconds)

    return AppLogsResponse(
        app_id=app_id,
        pod_name=result.get("pod_name"),
        container="runner",
        logs=[LogLine(**log) for log in result.get("logs", [])],
        truncated=result.get("truncated", False),
        error=result.get("error")
    )


@router.get("/{app_id}/events", response_model=AppEventsResponse)
async def get_app_events_endpoint(
    app_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get K8s events for an app's deployment."""
    try:
        await app_service.get_by_app_id(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    result = await get_app_events(app_id, limit)

    return AppEventsResponse(
        app_id=app_id,
        events=[K8sEvent(**event) for event in result.get("events", [])],
        deployment_phase=result.get("deployment_phase", "unknown"),
        error=result.get("error")
    )


# =============================================================================
# WebSocket Log Streaming
# =============================================================================

async def _authenticate_websocket(websocket: WebSocket) -> dict:
    """Authenticate a WebSocket connection via token query parameter.

    Returns user dict on success, or None after closing the socket on failure.
    """
    from jose import JWTError, jwt as jose_jwt
    from bson import ObjectId
    from config import SECRET_KEY, ALGORITHM
    from database import users_collection

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None

    try:
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return None
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return None

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return None

    return user


@router.websocket("/{app_id}/logs/stream")
async def stream_app_logs(websocket: WebSocket, app_id: str):
    """Stream live pod logs via WebSocket.

    Authentication is via `token` query parameter (browser WebSocket API
    cannot set custom headers).
    """
    user = await _authenticate_websocket(websocket)
    if not user:
        return

    # Verify user owns this app
    try:
        await app_service.get_by_app_id(app_id, user)
    except AppServiceError:
        await websocket.close(code=4004, reason="App not found")
        return

    await websocket.accept()

    from deployment.k8s_client import core_v1
    from config import PLATFORM_NAMESPACE

    if not core_v1:
        await websocket.send_json({"type": "error", "message": "Kubernetes client not available"})
        await websocket.close()
        return

    try:
        while True:
            # Find the pod
            try:
                pods = core_v1.list_namespaced_pod(
                    namespace=PLATFORM_NAMESPACE,
                    label_selector=f"app-id={app_id}"
                )
            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"K8s error: {e}"})
                await asyncio.sleep(5)
                continue

            if not pods.items:
                await websocket.send_json({"type": "status", "message": "No pod found, waiting..."})
                await asyncio.sleep(5)
                continue

            pod = pods.items[0]
            pod_name = pod.metadata.name

            if pod.status.phase not in ("Running", "Succeeded", "Failed"):
                await websocket.send_json({
                    "type": "status",
                    "message": f"Pod is {pod.status.phase}, waiting..."
                })
                await asyncio.sleep(3)
                continue

            # Stream logs using follow=True
            try:
                stream = core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=PLATFORM_NAMESPACE,
                    container="runner",
                    follow=True,
                    tail_lines=100,
                    timestamps=True,
                    _preload_content=False
                )

                await websocket.send_json({"type": "connected", "pod_name": pod_name})

                loop = asyncio.get_event_loop()
                while True:
                    # Read line in executor to avoid blocking the event loop
                    line_bytes = await loop.run_in_executor(
                        None, lambda: next(stream, None)
                    )
                    if line_bytes is None:
                        break

                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    # Parse K8s timestamp: "2024-01-15T10:30:00.123456789Z message"
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        log_data = {"type": "log", "timestamp": parts[0], "message": parts[1]}
                    else:
                        log_data = {"type": "log", "timestamp": None, "message": line}

                    await websocket.send_json(log_data)

                # Stream ended (pod terminated or restarted)
                await websocket.send_json({
                    "type": "status", "message": "Log stream ended, reconnecting..."
                })
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"Log stream error for app {app_id}: {e}")
                await websocket.send_json({"type": "error", "message": f"Stream error: {e}"})
                await asyncio.sleep(3)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for app {app_id}")
    except Exception as e:
        logger.error(f"WebSocket error for app {app_id}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


# =============================================================================
# Version History and Rollback
# =============================================================================

@router.get("/{app_id}/versions", response_model=VersionHistoryResponse)
async def get_versions(app_id: str, user: dict = Depends(get_current_user)):
    """Get version history for an app."""
    try:
        version_history, current_hash = await app_service.get_versions(app_id, user)
    except AppServiceError as e:
        raise handle_service_error(e)

    versions = [
        VersionEntry(
            code=v.get("code"),
            files=v.get("files"),
            deployed_at=v["deployed_at"],
            code_hash=v["code_hash"]
        )
        for v in version_history
    ]

    return VersionHistoryResponse(
        app_id=app_id,
        versions=versions,
        current_deployed_hash=current_hash
    )


@router.post("/{app_id}/rollback/{version_index}", response_model=AppResponse)
async def rollback(app_id: str, version_index: int, user: dict = Depends(get_current_user)):
    """Rollback to a previous version."""
    try:
        app = await app_service.rollback(app_id, version_index, user)
        return app_service.to_response(app)
    except AppServiceError as e:
        raise handle_service_error(e)
