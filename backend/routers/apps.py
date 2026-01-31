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
from database import apps_collection, settings_collection
from validation import validate_code, validate_multifile
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


def compute_code_hash(code_or_files) -> str:
    """Compute a short hash of code/files for comparison.
    Accepts either a string (single-file) or dict (multi-file).
    """
    if isinstance(code_or_files, dict):
        # Multi-file: hash all files sorted by name
        content = "".join(f"{k}:{v}" for k, v in sorted(code_or_files.items()))
    else:
        content = code_or_files or ""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# Helper Functions
# =============================================================================

async def get_user_app(app_id: str, user: dict) -> dict:
    """Fetch an app by app_id for the given user, raising 404 if not found."""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail=error_payload("NOT_FOUND", "App not found"))
    return app


async def get_allowed_imports_override() -> Optional[set]:
    settings = await settings_collection.find_one({"_id": "global"})
    allowed_imports = settings.get("allowed_imports") if settings else None
    if not allowed_imports:
        return None
    normalized = {
        item.strip().lower()
        for item in allowed_imports
        if isinstance(item, str) and item.strip()
    }
    return normalized or None


def build_app_response(app: dict) -> AppResponse:
    """Build an AppResponse from an app document."""
    return AppResponse(
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
    )


def build_app_detail_response(
    app: dict,
    has_unpublished_changes: bool
) -> AppDetailResponse:
    """Build an AppDetailResponse from an app document (single or multi-file)."""
    mode = app.get("mode", "single")

    return AppDetailResponse(
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
        last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None,
        # Single-file fields
        code=app.get("code") if mode == "single" else None,
        draft_code=app.get("draft_code") if mode == "single" else None,
        deployed_code=app.get("deployed_code") if mode == "single" else None,
        # Multi-file fields
        mode=mode,
        framework=app.get("framework"),
        entrypoint=app.get("entrypoint"),
        files=app.get("files") if mode == "multi" else None,
        draft_files=app.get("draft_files") if mode == "multi" else None,
        deployed_files=app.get("deployed_files") if mode == "multi" else None,
        # Common fields
        env_vars=app.get("env_vars"),
        deployed_at=app.get("deployed_at").isoformat() if app.get("deployed_at") else None,
        has_unpublished_changes=has_unpublished_changes,
        # Database selection
        database_id=app.get("database_id")
    )


def snapshot_version(app: dict) -> dict:
    """Create a version history entry from the current deployed state of an app."""
    mode = app.get("mode", "single")
    current_deployed_at = app.get("deployed_at") or app.get("last_deploy_at") or app["created_at"]

    if mode == "multi":
        current_deployed_files = app.get("deployed_files") or app.get("files", {})
        return {
            "files": current_deployed_files,
            "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
            "code_hash": compute_code_hash(current_deployed_files)
        }
    else:
        current_deployed_code = app.get("deployed_code") or app["code"]
        return {
            "code": current_deployed_code,
            "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
            "code_hash": compute_code_hash(current_deployed_code)
        }


def add_version_to_history(app: dict, version_entry: dict) -> list:
    """Add a version entry to history and limit to MAX_VERSION_HISTORY entries."""
    version_history = app.get("version_history", [])
    version_history.insert(0, version_entry)  # Most recent first
    return version_history[:MAX_VERSION_HISTORY]


async def deploy_and_update_status(
    app_id,
    app_doc: dict,
    user: dict,
    is_create: bool = False,
    new_deployed_code=None  # Can be str (single) or dict (multi-file)
) -> None:
    """
    Deploy an app and update its status in the database.
    Raises HTTPException on failure after updating error status.
    """
    try:
        if is_create:
            await create_app_deployment(app_doc, user)
        else:
            await update_app_deployment(app_doc, user)

        mode = app_doc.get("mode", "single")

        # Build success update
        success_update = {
            "status": "running",
            "deploy_stage": "running",
            "last_error": None
        }

        # If we have new deployed content, update version tracking fields
        if new_deployed_code is not None:
            if mode == "multi":
                success_update["deployed_files"] = new_deployed_code
                success_update["draft_files"] = None  # Clear draft after successful deploy
            else:
                success_update["deployed_code"] = new_deployed_code
                success_update["draft_code"] = None  # Clear draft after successful deploy
            success_update["deployed_at"] = datetime.utcnow()

        await apps_collection.update_one(
            {"_id": app_doc["_id"]},
            {"$set": success_update}
        )
    except Exception as e:
        error_msg = friendly_k8s_error(str(e))
        await apps_collection.update_one(
            {"_id": app_doc["_id"]},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
        )
        raise HTTPException(status_code=500, detail=error_payload("DEPLOY_FAILED", error_msg))


# =============================================================================
# Routes
# =============================================================================

@router.get("", response_model=List[AppResponse])
async def list_apps(user: dict = Depends(get_current_user)):
    apps = []
    async for app in apps_collection.find({"user_id": user["_id"], "status": {"$ne": "deleted"}}):
        apps.append(build_app_response(app))
    return apps


@router.post("", response_model=AppResponse)
async def create_app(app_data: AppCreate, user: dict = Depends(get_current_user)):
    mode = app_data.mode or "single"
    allowed_imports_override = await get_allowed_imports_override()

    # Validate database_id if provided
    database_id = app_data.database_id
    if database_id:
        databases = user.get("databases", [])
        if not any(db["id"] == database_id for db in databases):
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_DATABASE", "Database not found")
            )

    # Validate based on mode
    if mode == "multi":
        if not app_data.files:
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "files required for multi-file mode")
            )
        if not app_data.framework:
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "framework required for multi-file mode")
            )
        if app_data.framework not in ("fastapi", "fasthtml"):
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "framework must be 'fastapi' or 'fasthtml'")
            )

        entrypoint = app_data.entrypoint or "app.py"
        is_valid, error_msg, error_line, error_file = validate_multifile(
            app_data.files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}",
                                     {"line": error_line, "file": error_file})
            )
    else:
        # Single-file mode
        if not app_data.code:
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "code required for single-file mode")
            )
        is_valid, error_msg, error_line = validate_code(
            app_data.code,
            allowed_imports_override=allowed_imports_override
        )
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
        "mode": mode,
        "env_vars": app_data.env_vars or {},
        "database_id": database_id,  # May be None (uses user's default)
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": now,
        "created_at": now,
        "last_activity": now,
        "deployment_url": f"https://app-{app_id}.{APP_DOMAIN}",
        "version_history": []
    }

    if mode == "multi":
        app_doc["framework"] = app_data.framework
        app_doc["entrypoint"] = app_data.entrypoint or "app.py"
        app_doc["files"] = app_data.files
        app_doc["deployed_files"] = app_data.files
        app_doc["deployed_at"] = now
        app_doc["draft_files"] = None
    else:
        app_doc["code"] = app_data.code
        app_doc["deployed_code"] = app_data.code
        app_doc["deployed_at"] = now
        app_doc["draft_code"] = None

    result = await apps_collection.insert_one(app_doc)
    app_doc["_id"] = result.inserted_id

    # Deploy to Kubernetes
    await deploy_and_update_status(app_doc["_id"], app_doc, user, is_create=True)

    updated_app = await apps_collection.find_one({"_id": result.inserted_id})
    return build_app_response(updated_app)


@router.get("/{app_id}", response_model=AppDetailResponse)
async def get_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")

    # Compute whether there are unpublished changes
    if mode == "multi":
        # Multi-file: compare draft_files (or files) against deployed_files
        deployed_files = app.get("deployed_files") or app.get("files", {})
        draft_files = app.get("draft_files")
        current_files = draft_files if draft_files is not None else app.get("files", {})
        has_unpublished_changes = compute_code_hash(current_files) != compute_code_hash(deployed_files)
    else:
        # Single-file: migration for legacy apps without deployed_code
        deployed_code = app.get("deployed_code")
        if deployed_code is None:
            deployed_code = app["code"]
            # Persist migration
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"deployed_code": deployed_code, "deployed_at": app.get("last_deploy_at") or app["created_at"]}}
            )
            app["deployed_code"] = deployed_code

        draft_code = app.get("draft_code")
        current_code = draft_code if draft_code is not None else app["code"]
        has_unpublished_changes = compute_code_hash(current_code) != compute_code_hash(deployed_code)

    return build_app_detail_response(app, has_unpublished_changes)


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(app_id: str, app_data: AppUpdate, user: dict = Depends(get_current_user)):
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")
    allowed_imports_override = await get_allowed_imports_override()

    update_data = {}
    needs_redeploy = False
    new_deployed_content = None  # code string or files dict

    if app_data.name is not None:
        update_data["name"] = app_data.name

    # Handle code/files update based on mode
    if mode == "multi":
        if app_data.files is not None:
            # Validate multi-file
            entrypoint = app.get("entrypoint", "app.py")
            is_valid, error_msg, error_line, error_file = validate_multifile(
                app_data.files,
                entrypoint,
                allowed_imports_override=allowed_imports_override
            )
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}",
                                         {"line": error_line, "file": error_file})
                )
            update_data["files"] = app_data.files
            new_deployed_content = app_data.files
            needs_redeploy = True
    else:
        if app_data.code is not None:
            # Validate single-file code
            is_valid, error_msg, error_line = validate_code(
                app_data.code,
                allowed_imports_override=allowed_imports_override
            )
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}", {"line": error_line})
                )
            update_data["code"] = app_data.code
            new_deployed_content = app_data.code
            needs_redeploy = True

    if app_data.env_vars is not None:
        update_data["env_vars"] = app_data.env_vars
        needs_redeploy = True

    # Handle database_id change
    if app_data.database_id is not None:
        # Validate the database exists for this user
        databases = user.get("databases", [])
        if not any(db["id"] == app_data.database_id for db in databases):
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_DATABASE", "Database not found")
            )
        update_data["database_id"] = app_data.database_id
        needs_redeploy = True  # Changing database requires redeploy to update PLATFORM_MONGO_URI

    if needs_redeploy:
        update_data["status"] = "deploying"
        update_data["deploy_stage"] = "deploying"
        update_data["last_error"] = None
        update_data["last_deploy_at"] = datetime.utcnow()

        # Snapshot current deployed code/files to version history before deploying
        version_entry = snapshot_version(app)
        update_data["version_history"] = add_version_to_history(app, version_entry)

    if not update_data:
        raise HTTPException(status_code=400, detail=error_payload("INVALID_REQUEST", "No fields to update"))

    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": update_data}
    )

    # Update deployment if code/files or env_vars changed
    if needs_redeploy:
        updated_app = await apps_collection.find_one({"_id": app["_id"]})
        await deploy_and_update_status(
            app["_id"], updated_app, user,
            is_create=False,
            new_deployed_code=new_deployed_content
        )

    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    return build_app_response(updated_app)


@router.put("/{app_id}/draft", response_model=AppDetailResponse)
async def save_draft(app_id: str, draft: DraftUpdate, user: dict = Depends(get_current_user)):
    """Save draft code/files without deploying"""
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")
    allowed_imports_override = await get_allowed_imports_override()

    if mode == "multi":
        if not draft.files:
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "files required for multi-file mode draft")
            )
        # Validate draft files
        entrypoint = app.get("entrypoint", "app.py")
        is_valid, error_msg, error_line, error_file = validate_multifile(
            draft.files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Code validation failed: {error_msg}",
                                     {"line": error_line, "file": error_file})
            )

        # Update draft_files and files fields, no K8s changes
        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {
                "files": draft.files,
                "draft_files": draft.files,
                "last_activity": datetime.utcnow()
            }}
        )

        # Fetch updated app and compute changes
        updated_app = await apps_collection.find_one({"_id": app["_id"]})
        deployed_files = updated_app.get("deployed_files") or updated_app.get("files", {})
        has_unpublished_changes = compute_code_hash(draft.files) != compute_code_hash(deployed_files)
    else:
        if not draft.code:
            raise HTTPException(
                status_code=400,
                detail=error_payload("INVALID_REQUEST", "code required for single-file mode draft")
            )
        # Validate draft code (still need valid syntax)
        is_valid, error_msg, error_line = validate_code(
            draft.code,
            allowed_imports_override=allowed_imports_override
        )
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

        # Fetch updated app and compute changes
        updated_app = await apps_collection.find_one({"_id": app["_id"]})
        deployed_code = updated_app.get("deployed_code") or updated_app["code"]
        has_unpublished_changes = compute_code_hash(draft.code) != compute_code_hash(deployed_code)

    return build_app_detail_response(updated_app, has_unpublished_changes)


@router.delete("/{app_id}")
async def delete_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await get_user_app(app_id, user)
    
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
    """Clone an existing app - copies code/files and env var keys (not values)"""
    source_app = await get_user_app(app_id, user)
    mode = source_app.get("mode", "single")
    allowed_imports_override = await get_allowed_imports_override()

    # Generate unique app_id for the clone
    new_app_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

    # Clone name with "-copy" suffix
    base_name = source_app["name"]
    # Remove existing "-copy" suffix if present, then add it
    if base_name.endswith("-copy"):
        base_name = base_name[:-5]
    new_name = f"{base_name}-copy"

    # Clone env vars but clear values (keep keys only)
    cloned_env_vars = {}
    if source_app.get("env_vars"):
        for key in source_app["env_vars"].keys():
            cloned_env_vars[key] = ""  # Empty value

    # Create cloned app document
    now = datetime.utcnow()
    cloned_app_doc = {
        "user_id": user["_id"],
        "app_id": new_app_id,
        "name": new_name,
        "mode": mode,
        "env_vars": cloned_env_vars,
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": now,
        "created_at": now,
        "last_activity": now,
        "deployment_url": f"https://app-{new_app_id}.{APP_DOMAIN}",
        "version_history": []
    }

    if mode == "multi":
        cloned_files = source_app.get("files", {})
        # Validate cloned files
        entrypoint = source_app.get("entrypoint", "app.py")
        is_valid, error_msg, error_line, error_file = validate_multifile(
            cloned_files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Cloned code validation failed: {error_msg}",
                                     {"line": error_line, "file": error_file})
            )
        cloned_app_doc["framework"] = source_app.get("framework")
        cloned_app_doc["entrypoint"] = entrypoint
        cloned_app_doc["files"] = cloned_files
        cloned_app_doc["deployed_files"] = cloned_files
        cloned_app_doc["deployed_at"] = now
        cloned_app_doc["draft_files"] = None
    else:
        cloned_code = source_app["code"]
        # Validate cloned code
        is_valid, error_msg, error_line = validate_code(
            cloned_code,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Cloned code validation failed: {error_msg}", {"line": error_line})
            )
        cloned_app_doc["code"] = cloned_code
        cloned_app_doc["deployed_code"] = cloned_code
        cloned_app_doc["deployed_at"] = now
        cloned_app_doc["draft_code"] = None

    result = await apps_collection.insert_one(cloned_app_doc)
    cloned_app_doc["_id"] = result.inserted_id

    # Deploy cloned app to Kubernetes
    await deploy_and_update_status(cloned_app_doc["_id"], cloned_app_doc, user, is_create=True)

    updated_app = await apps_collection.find_one({"_id": result.inserted_id})
    return build_app_response(updated_app)


@router.get("/{app_id}/status", response_model=AppStatusResponse)
async def get_app_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get deployment status for an app"""
    app = await get_user_app(app_id, user)
    
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
    """Validate code/files before creating an app"""
    allowed_imports_override = await get_allowed_imports_override()
    if payload.files:
        # Multi-file validation
        entrypoint = payload.entrypoint or "app.py"
        is_valid, error_msg, error_line, error_file = validate_multifile(
            payload.files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": error_file}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    elif payload.code:
        # Single-file validation
        is_valid, error_msg, error_line = validate_code(
            payload.code,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": None}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    else:
        return {"valid": False, "message": "No code or files provided", "line": None, "file": None}


@router.post("/{app_id}/validate")
async def validate_existing_app(app_id: str, payload: ValidateRequest, user: dict = Depends(get_current_user)):
    """Validate code/files for an existing app"""
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")
    allowed_imports_override = await get_allowed_imports_override()

    if mode == "multi" or payload.files:
        # Multi-file validation
        files = payload.files or app.get("files", {})
        entrypoint = payload.entrypoint or app.get("entrypoint", "app.py")
        is_valid, error_msg, error_line, error_file = validate_multifile(
            files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": error_file}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}
    else:
        # Single-file validation
        code = payload.code or app.get("code", "")
        is_valid, error_msg, error_line = validate_code(
            code,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            return {"valid": False, "message": error_msg, "line": error_line, "file": None}
        return {"valid": True, "message": "Code validation passed", "line": None, "file": None}


@router.get("/{app_id}/deploy-status", response_model=AppDeployStatusResponse)
async def get_app_deploy_status(app_id: str, user: dict = Depends(get_current_user)):
    app = await get_user_app(app_id, user)

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
    app = await get_user_app(app_id, user)
    
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
    await get_user_app(app_id, user)  # Verify app exists and user owns it

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
    await get_user_app(app_id, user)  # Verify app exists and user owns it

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
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")

    version_history = app.get("version_history", [])

    # Convert to VersionEntry objects
    versions = [
        VersionEntry(
            code=v.get("code"),
            files=v.get("files"),
            deployed_at=v["deployed_at"],
            code_hash=v["code_hash"]
        )
        for v in version_history
    ]

    # Get current deployed hash
    if mode == "multi":
        deployed_content = app.get("deployed_files") or app.get("files", {})
    else:
        deployed_content = app.get("deployed_code") or app.get("code", "")
    current_hash = compute_code_hash(deployed_content)

    return VersionHistoryResponse(
        app_id=app_id,
        versions=versions,
        current_deployed_hash=current_hash
    )


@router.post("/{app_id}/rollback/{version_index}", response_model=AppResponse)
async def rollback(app_id: str, version_index: int, user: dict = Depends(get_current_user)):
    """Rollback to a previous version"""
    app = await get_user_app(app_id, user)
    mode = app.get("mode", "single")
    allowed_imports_override = await get_allowed_imports_override()

    version_history = app.get("version_history", [])

    if version_index < 0 or version_index >= len(version_history):
        raise HTTPException(
            status_code=400,
            detail=error_payload("INVALID_VERSION", f"Version index {version_index} is out of range (0-{len(version_history)-1})")
        )

    # Get the code/files from the specified version
    rollback_version = version_history[version_index]

    # Snapshot current deployed content to version history before rollback
    version_entry = snapshot_version(app)
    new_version_history = add_version_to_history(app, version_entry)

    now = datetime.utcnow()
    update_set = {
        "status": "deploying",
        "deploy_stage": "deploying",
        "last_error": None,
        "last_deploy_at": now,
        "version_history": new_version_history
    }

    if mode == "multi":
        rollback_files = rollback_version.get("files", {})
        # Validate the files
        entrypoint = app.get("entrypoint", "app.py")
        is_valid, error_msg, error_line, error_file = validate_multifile(
            rollback_files,
            entrypoint,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Rollback code validation failed: {error_msg}",
                                     {"line": error_line, "file": error_file})
            )
        update_set["files"] = rollback_files
        new_deployed_content = rollback_files
    else:
        rollback_code = rollback_version.get("code", "")
        # Validate the code
        is_valid, error_msg, error_line = validate_code(
            rollback_code,
            allowed_imports_override=allowed_imports_override
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_payload("VALIDATION_FAILED", f"Rollback code validation failed: {error_msg}", {"line": error_line})
            )
        update_set["code"] = rollback_code
        new_deployed_content = rollback_code

    # Update app with rollback content
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": update_set}
    )

    # Deploy the rollback
    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    await deploy_and_update_status(
        app["_id"], updated_app, user,
        is_create=False,
        new_deployed_code=new_deployed_content
    )

    final_app = await apps_collection.find_one({"_id": app["_id"]})
    return build_app_response(final_app)
