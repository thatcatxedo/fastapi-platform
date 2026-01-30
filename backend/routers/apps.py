"""
App management routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import secrets
import string
import logging

from models import (
    AppCreate, AppUpdate, AppResponse, AppDetailResponse, AppStatusResponse,
    AppDeployStatusResponse, ValidateRequest, AppLogsResponse, AppEventsResponse, LogLine, K8sEvent
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
    app_doc = {
        "user_id": user["_id"],
        "app_id": app_id,
        "name": app_data.name,
        "code": app_data.code,
        "env_vars": app_data.env_vars or {},
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "deployment_url": f"https://app-{app_id}.{APP_DOMAIN}"
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
        last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None
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
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": "running", "deploy_stage": "running", "last_error": None}}
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
    cloned_app_doc = {
        "user_id": user["_id"],
        "app_id": new_app_id,
        "name": new_name,
        "code": cloned_code,
        "env_vars": cloned_env_vars,
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "deployment_url": f"https://app-{new_app_id}.{APP_DOMAIN}"
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
