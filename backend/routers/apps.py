"""
App management routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import secrets
import string
import logging

import hashlib

from models import (
    AppCreate, AppUpdate, AppResponse, AppDetailResponse, AppStatusResponse,
    AppDeployStatusResponse, ValidateRequest, AppLogsResponse, AppEventsResponse, 
    LogLine, K8sEvent, DraftUpdate, VersionEntry, VersionHistoryResponse
)
from auth import get_current_user
from database import apps_collection
from validation import validate_code
from utils import error_payload, friendly_k8s_error
from config import APP_DOMAIN
from deployment import (
    create_app_deployment,
    delete_app_deployment,
    update_app_deployment,
    get_deployment_status,
    get_pod_logs,
    get_app_events
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["apps"])

# Maximum number of versions to keep in history
MAX_VERSION_HISTORY = 10


def compute_code_hash(code: str) -> str:
    """Compute a short hash of code for comparison"""
    return hashlib.sha256(code.encode()).hexdigest()[:16]


@router.get("", response_model=List[AppResponse])
async def list_apps(user: dict = Depends(get_current_user)):
    apps = []
    async for app in apps_collection.find({"user_id": user["_id"], "status": {"$ne": "deleted"}}):
        apps.append(AppResponse(
            id=str(app["_id"]),
            app_id=app["app_id"],
            name=app["name"],
            status=app["status"],
            created_at=app["created_at"].isoformat(),
            last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
            deployment_url=app["deployment_url"],
            error_message=app.get("error_message"),
            deploy_stage=app.get("deploy_stage"),
            last_error=app.get("last_error"),
            last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None
        ))
    return apps


@router.post("", response_model=AppResponse)
async def create_app(app_data: AppCreate, user: dict = Depends(get_current_user)):
    # Validate code
    is_valid, error_msg, error_line = validate_code(app_data.code)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}", {"line": error_line})
        )
    
    # Generate unique app_id (lowercase alphanumeric only for Kubernetes compliance)
    app_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    
    # Create app document
    now = datetime.utcnow()
    app_doc = {
        "user_id": user["_id"],
        "app_id": app_id,
        "name": app_data.name,
        "code": app_data.code,
        "env_vars": app_data.env_vars or {},
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": now,
        "created_at": now,
        "last_activity": now,
        "deployment_url": f"https://app-{app_id}.{APP_DOMAIN}",
        # Version tracking fields
        "deployed_code": app_data.code,
        "deployed_at": now,
        "draft_code": None,
        "version_history": []
    }

    result = await apps_collection.insert_one(app_doc)
    app_doc["_id"] = result.inserted_id
    
    # Deploy to Kubernetes
    try:
        await create_app_deployment(app_doc, user)
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "running", "deploy_stage": "running", "last_error": None}}
        )
    except Exception as e:
        error_msg = friendly_k8s_error(str(e))
        
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
        )
        raise HTTPException(status_code=500, detail=error_payload("DEPLOY_FAILED", error_msg))
    
    updated_app = await apps_collection.find_one({"_id": result.inserted_id})
    return AppResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message"),
        deploy_stage=updated_app.get("deploy_stage"),
        last_error=updated_app.get("last_error"),
        last_deploy_at=updated_app.get("last_deploy_at").isoformat() if updated_app.get("last_deploy_at") else None
    )


@router.get("/{app_id}", response_model=AppDetailResponse)
async def get_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    # Migration: if deployed_code doesn't exist, set it to code
    deployed_code = app.get("deployed_code")
    if deployed_code is None:
        deployed_code = app["code"]
        # Persist migration
        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {"deployed_code": deployed_code, "deployed_at": app.get("last_deploy_at") or app["created_at"]}}
        )
    
    # Get draft code (falls back to deployed code if not set)
    draft_code = app.get("draft_code")
    
    # Compute whether there are unpublished changes
    # Compare draft_code (or code) against deployed_code
    current_code = draft_code if draft_code is not None else app["code"]
    has_unpublished_changes = compute_code_hash(current_code) != compute_code_hash(deployed_code)
    
    return AppDetailResponse(
        id=str(app["_id"]),
        app_id=app["app_id"],
        name=app["name"],
        code=app["code"],
        env_vars=app.get("env_vars"),
        status=app["status"],
        created_at=app["created_at"].isoformat(),
        last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
        deployment_url=app["deployment_url"],
        error_message=app.get("error_message"),
        deploy_stage=app.get("deploy_stage"),
        last_error=app.get("last_error"),
        last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None,
        draft_code=draft_code,
        deployed_code=deployed_code,
        deployed_at=app.get("deployed_at").isoformat() if app.get("deployed_at") else None,
        has_unpublished_changes=has_unpublished_changes
    )


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(app_id: str, app_data: AppUpdate, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    update_data = {}
    needs_redeploy = False

    if app_data.name is not None:
        update_data["name"] = app_data.name
    if app_data.code is not None:
        # Validate code
        is_valid, error_msg, error_line = validate_code(app_data.code)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}", {"line": error_line})
            )
        update_data["code"] = app_data.code
        needs_redeploy = True
    if app_data.env_vars is not None:
        update_data["env_vars"] = app_data.env_vars
        needs_redeploy = True

    if needs_redeploy:
        update_data["status"] = "deploying"
        update_data["deploy_stage"] = "deploying"
        update_data["last_error"] = None
        update_data["last_deploy_at"] = datetime.utcnow()
        
        # Snapshot current deployed code to version history before deploying
        current_deployed_code = app.get("deployed_code") or app["code"]
        current_deployed_at = app.get("deployed_at") or app.get("last_deploy_at") or app["created_at"]
        
        version_entry = {
            "code": current_deployed_code,
            "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
            "code_hash": compute_code_hash(current_deployed_code)
        }
        
        # Get existing version history and add new entry
        version_history = app.get("version_history", [])
        version_history.insert(0, version_entry)  # Most recent first
        
        # Limit to MAX_VERSION_HISTORY entries
        version_history = version_history[:MAX_VERSION_HISTORY]
        update_data["version_history"] = version_history

    if not update_data:
        raise HTTPException(status_code=400, detail=error_payload("INVALID_REQUEST", "No fields to update"))
    
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": update_data}
    )

    # Update deployment if code or env_vars changed
    if needs_redeploy:
        updated_app = await apps_collection.find_one({"_id": app["_id"]})
        try:
            await update_app_deployment(updated_app, user)
            # On successful deploy, update deployed_code and clear draft
            new_deployed_code = app_data.code if app_data.code else app["code"]
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {
                    "status": "running", 
                    "deploy_stage": "running", 
                    "last_error": None,
                    "deployed_code": new_deployed_code,
                    "deployed_at": datetime.utcnow(),
                    "draft_code": None  # Clear draft after successful deploy
                }}
            )
        except Exception as e:
            error_msg = friendly_k8s_error(str(e))
            
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
            )
            raise HTTPException(status_code=500, detail=error_payload("DEPLOY_FAILED", error_msg))
    
    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    return AppResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message"),
        deploy_stage=updated_app.get("deploy_stage"),
        last_error=updated_app.get("last_error"),
        last_deploy_at=updated_app.get("last_deploy_at").isoformat() if updated_app.get("last_deploy_at") else None
    )


@router.put("/{app_id}/draft", response_model=AppDetailResponse)
async def save_draft(app_id: str, draft: DraftUpdate, user: dict = Depends(get_current_user)):
    """Save draft code without deploying"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    # Validate draft code (still need valid syntax)
    is_valid, error_msg, error_line = validate_code(draft.code)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}", {"line": error_line})
        )
    
    # Update draft_code and code fields, no K8s changes
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {
            "code": draft.code,
            "draft_code": draft.code,
            "last_activity": datetime.utcnow()
        }}
    )
    
    # Fetch updated app and return
    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    
    # Get deployed_code for comparison
    deployed_code = updated_app.get("deployed_code") or updated_app["code"]
    has_unpublished_changes = compute_code_hash(draft.code) != compute_code_hash(deployed_code)
    
    return AppDetailResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        code=updated_app["code"],
        env_vars=updated_app.get("env_vars"),
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message"),
        deploy_stage=updated_app.get("deploy_stage"),
        last_error=updated_app.get("last_error"),
        last_deploy_at=updated_app.get("last_deploy_at").isoformat() if updated_app.get("last_deploy_at") else None,
        draft_code=updated_app.get("draft_code"),
        deployed_code=deployed_code,
        deployed_at=updated_app.get("deployed_at").isoformat() if updated_app.get("deployed_at") else None,
        has_unpublished_changes=has_unpublished_changes
    )


@router.delete("/{app_id}")
async def delete_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    # Delete from Kubernetes
    try:
        await delete_app_deployment(app, user)
    except Exception as e:
        logger.error(f"Error deleting deployment: {e}")
    
    # Mark as deleted in database
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {"status": "deleted"}}
    )
    
    return {"success": True, "message": "App deleted"}


@router.post("/{app_id}/clone", response_model=AppResponse)
async def clone_app(app_id: str, user: dict = Depends(get_current_user)):
    """Clone an existing app - copies code and env var keys (not values)"""
    # Find the source app
    source_app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not source_app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    # Generate unique app_id for the clone
    new_app_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    
    # Clone name with "-copy" suffix
    base_name = source_app["name"]
    # Remove existing "-copy" suffix if present, then add it
    if base_name.endswith("-copy"):
        base_name = base_name[:-5]
    new_name = f"{base_name}-copy"
    
    # Clone code
    cloned_code = source_app["code"]
    
    # Clone env vars but clear values (keep keys only)
    cloned_env_vars = {}
    if source_app.get("env_vars"):
        for key in source_app["env_vars"].keys():
            cloned_env_vars[key] = ""  # Empty value
    
    # Validate cloned code
    is_valid, error_msg, error_line = validate_code(cloned_code)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_payload("VALIDATION_FAILED", f"Cloned code validation failed: {error_msg}", {"line": error_line})
        )
    
    # Create cloned app document
    now = datetime.utcnow()
    cloned_app_doc = {
        "user_id": user["_id"],
        "app_id": new_app_id,
        "name": new_name,
        "code": cloned_code,
        "env_vars": cloned_env_vars,
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": now,
        "created_at": now,
        "last_activity": now,
        "deployment_url": f"https://app-{new_app_id}.{APP_DOMAIN}",
        # Version tracking fields - start fresh for cloned app
        "deployed_code": cloned_code,
        "deployed_at": now,
        "draft_code": None,
        "version_history": []
    }

    result = await apps_collection.insert_one(cloned_app_doc)
    cloned_app_doc["_id"] = result.inserted_id
    
    # Deploy cloned app to Kubernetes
    try:
        await create_app_deployment(cloned_app_doc, user)
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "running", "deploy_stage": "running", "last_error": None}}
        )
    except Exception as e:
        error_msg = friendly_k8s_error(str(e))
        
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
        )
        raise HTTPException(status_code=500, detail=error_payload("DEPLOY_FAILED", error_msg))
    
    updated_app = await apps_collection.find_one({"_id": result.inserted_id})
    return AppResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message"),
        deploy_stage=updated_app.get("deploy_stage"),
        last_error=updated_app.get("last_error"),
        last_deploy_at=updated_app.get("last_deploy_at").isoformat() if updated_app.get("last_deploy_at") else None
    )


@router.get("/{app_id}/status", response_model=AppStatusResponse)
async def get_app_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get deployment status for an app"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    pod_status = None
    deployment_ready = False
    
    # Check Kubernetes deployment status if available
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


@router.post("/validate")
async def validate_app_code(payload: ValidateRequest, user: dict = Depends(get_current_user)):
    is_valid, error_msg, error_line = validate_code(payload.code)
    if not is_valid:
        return {"valid": False, "message": error_msg, "line": error_line}
    return {"valid": True, "message": "Code validation passed", "line": None}


@router.post("/{app_id}/validate")
async def validate_existing_app(app_id: str, payload: ValidateRequest, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    is_valid, error_msg, error_line = validate_code(payload.code)
    if not is_valid:
        return {"valid": False, "message": error_msg, "line": error_line}
    return {"valid": True, "message": "Code validation passed", "line": None}


@router.get("/{app_id}/deploy-status", response_model=AppDeployStatusResponse)
async def get_app_deploy_status(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))

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


@router.post("/{app_id}/activity")
async def record_activity(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {"last_activity": datetime.utcnow()}}
    )
    
    return {"success": True}


@router.get("/{app_id}/logs", response_model=AppLogsResponse)
async def get_app_logs(
    app_id: str,
    tail_lines: int = 100,
    since_seconds: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """Get live pod logs for an app"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))

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
    """Get K8s events for an app's deployment"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))

    result = await get_app_events(app_id, limit)

    return AppEventsResponse(
        app_id=app_id,
        events=[K8sEvent(**event) for event in result.get("events", [])],
        deployment_phase=result.get("deployment_phase", "unknown"),
        error=result.get("error")
    )


@router.get("/{app_id}/versions", response_model=VersionHistoryResponse)
async def get_versions(app_id: str, user: dict = Depends(get_current_user)):
    """Get version history for an app"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    version_history = app.get("version_history", [])
    
    # Convert to VersionEntry objects
    versions = []
    for v in version_history:
        versions.append(VersionEntry(
            code=v["code"],
            deployed_at=v["deployed_at"],
            code_hash=v["code_hash"]
        ))
    
    # Get current deployed hash
    deployed_code = app.get("deployed_code") or app["code"]
    current_hash = compute_code_hash(deployed_code)
    
    return VersionHistoryResponse(
        app_id=app_id,
        versions=versions,
        current_deployed_hash=current_hash
    )


@router.post("/{app_id}/rollback/{version_index}", response_model=AppResponse)
async def rollback(app_id: str, version_index: int, user: dict = Depends(get_current_user)):
    """Rollback to a previous version"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    
    version_history = app.get("version_history", [])
    
    if version_index < 0 or version_index >= len(version_history):
        raise HTTPException(
            status_code=400,
            detail=error_payload("INVALID_VERSION", f"Version index {version_index} is out of range (0-{len(version_history)-1})")
        )
    
    # Get the code from the specified version
    rollback_version = version_history[version_index]
    rollback_code = rollback_version["code"]
    
    # Validate the code (should be valid but check anyway)
    is_valid, error_msg, error_line = validate_code(rollback_code)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_payload("VALIDATION_FAILED", f"Rollback code validation failed: {error_msg}", {"line": error_line})
        )
    
    # Snapshot current deployed code to version history before rollback
    current_deployed_code = app.get("deployed_code") or app["code"]
    current_deployed_at = app.get("deployed_at") or app.get("last_deploy_at") or app["created_at"]
    
    version_entry = {
        "code": current_deployed_code,
        "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
        "code_hash": compute_code_hash(current_deployed_code)
    }
    
    # Add to history and limit size
    new_version_history = [version_entry] + version_history
    new_version_history = new_version_history[:MAX_VERSION_HISTORY]
    
    # Update app with rollback code
    now = datetime.utcnow()
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {
            "code": rollback_code,
            "status": "deploying",
            "deploy_stage": "deploying",
            "last_error": None,
            "last_deploy_at": now,
            "version_history": new_version_history
        }}
    )
    
    # Deploy the rollback
    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    try:
        await update_app_deployment(updated_app, user)
        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {
                "status": "running",
                "deploy_stage": "running",
                "last_error": None,
                "deployed_code": rollback_code,
                "deployed_at": now,
                "draft_code": None
            }}
        )
    except Exception as e:
        error_msg = friendly_k8s_error(str(e))
        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
        )
        raise HTTPException(status_code=500, detail=error_payload("DEPLOY_FAILED", error_msg))
    
    final_app = await apps_collection.find_one({"_id": app["_id"]})
    return AppResponse(
        id=str(final_app["_id"]),
        app_id=final_app["app_id"],
        name=final_app["name"],
        status=final_app["status"],
        created_at=final_app["created_at"].isoformat(),
        last_activity=final_app.get("last_activity").isoformat() if final_app.get("last_activity") else None,
        deployment_url=final_app["deployment_url"],
        error_message=final_app.get("error_message"),
        deploy_stage=final_app.get("deploy_stage"),
        last_error=final_app.get("last_error"),
        last_deploy_at=final_app.get("last_deploy_at").isoformat() if final_app.get("last_deploy_at") else None
    )
