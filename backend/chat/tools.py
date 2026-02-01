"""
Tool definitions for AI chat assistant.
Claude can use these tools to help users build and manage apps.
"""
import logging
from typing import Any, Dict, List, Optional
import secrets
import string
from datetime import datetime

from database import apps_collection, users_collection
from deployment import (
    create_app_deployment,
    delete_app_deployment,
    update_app_deployment,
    get_pod_logs
)
from validation import validate_code, validate_multifile
from config import APP_DOMAIN

logger = logging.getLogger(__name__)


# Tool definitions in Claude's tool format
TOOLS = [
    {
        "name": "create_app",
        "description": "Create and deploy a new application. Use 'code' for single-file apps or 'files' for multi-file apps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the app (e.g., 'my-todo-api')"
                },
                "code": {
                    "type": "string",
                    "description": "Python code for single-file apps. Must define an 'app' instance (FastAPI or FastHTML)."
                },
                "files": {
                    "type": "object",
                    "description": "For multi-file apps: dictionary of {filename: code}. Must include app.py as entrypoint.",
                    "additionalProperties": {"type": "string"}
                },
                "framework": {
                    "type": "string",
                    "enum": ["fastapi", "fasthtml"],
                    "description": "Framework type. Required for multi-file apps."
                },
                "database_id": {
                    "type": "string",
                    "description": "Optional database ID to connect. If not specified, uses user's default database."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_app",
        "description": "Update an existing app's code and redeploy it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to update"
                },
                "code": {
                    "type": "string",
                    "description": "New code for single-file apps"
                },
                "files": {
                    "type": "object",
                    "description": "New files for multi-file apps: {filename: code}",
                    "additionalProperties": {"type": "string"}
                },
                "name": {
                    "type": "string",
                    "description": "Optional new name for the app"
                }
            },
            "required": ["app_id"]
        }
    },
    {
        "name": "get_app",
        "description": "Get details about an app including its code, status, and URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to retrieve"
                }
            },
            "required": ["app_id"]
        }
    },
    {
        "name": "get_app_logs",
        "description": "Get recent logs from an app's deployment. Useful for debugging errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to get logs for"
                },
                "tail_lines": {
                    "type": "integer",
                    "description": "Number of recent log lines to fetch (default: 50)",
                    "default": 50
                }
            },
            "required": ["app_id"]
        }
    },
    {
        "name": "list_apps",
        "description": "List all of the user's apps with their status and URLs.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "delete_app",
        "description": "Delete an app and its deployment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to delete"
                }
            },
            "required": ["app_id"]
        }
    },
    {
        "name": "list_databases",
        "description": "List the user's available MongoDB databases.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


async def execute_tool(name: str, input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """
    Execute a tool and return the result.

    Args:
        name: Tool name
        input_data: Tool input parameters
        user: Current user document

    Returns:
        Tool execution result
    """
    try:
        if name == "create_app":
            return await _create_app(input_data, user)
        elif name == "update_app":
            return await _update_app(input_data, user)
        elif name == "get_app":
            return await _get_app(input_data, user)
        elif name == "get_app_logs":
            return await _get_app_logs(input_data, user)
        elif name == "list_apps":
            return await _list_apps(user)
        elif name == "delete_app":
            return await _delete_app(input_data, user)
        elif name == "list_databases":
            return await _list_databases(user)
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        logger.error(f"Tool execution error ({name}): {e}")
        return {"error": str(e)}


async def _create_app(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Create and deploy a new app."""
    name = input_data.get("name")
    code = input_data.get("code")
    files = input_data.get("files")
    framework = input_data.get("framework")
    database_id = input_data.get("database_id")

    if not name:
        return {"error": "App name is required"}

    # Determine mode
    if files:
        mode = "multi"
        if not framework:
            return {"error": "framework is required for multi-file apps"}
        if framework not in ("fastapi", "fasthtml"):
            return {"error": "framework must be 'fastapi' or 'fasthtml'"}
        if "app.py" not in files:
            return {"error": "Multi-file apps must include app.py as entrypoint"}
    elif code:
        mode = "single"
    else:
        return {"error": "Either 'code' or 'files' is required"}

    # Validate database_id if provided
    if database_id:
        databases = user.get("databases", [])
        if not any(db["id"] == database_id for db in databases):
            return {"error": f"Database '{database_id}' not found"}

    # Validate code
    if mode == "multi":
        is_valid, error_msg, error_line, error_file = validate_multifile(files, "app.py")
        if not is_valid:
            return {"error": f"Code validation failed in {error_file} line {error_line}: {error_msg}"}
    else:
        is_valid, error_msg, error_line = validate_code(code)
        if not is_valid:
            return {"error": f"Code validation failed at line {error_line}: {error_msg}"}

    # Generate unique app_id
    app_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

    # Create app document
    now = datetime.utcnow()
    app_doc = {
        "user_id": user["_id"],
        "app_id": app_id,
        "name": name,
        "mode": mode,
        "env_vars": {},
        "database_id": database_id,
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
        app_doc["framework"] = framework
        app_doc["entrypoint"] = "app.py"
        app_doc["files"] = files
        app_doc["deployed_files"] = files
        app_doc["deployed_at"] = now
        app_doc["draft_files"] = None
    else:
        app_doc["code"] = code
        app_doc["deployed_code"] = code
        app_doc["deployed_at"] = now
        app_doc["draft_code"] = None

    result = await apps_collection.insert_one(app_doc)
    app_doc["_id"] = result.inserted_id

    # Deploy to Kubernetes
    try:
        await create_app_deployment(app_doc, user)
        await apps_collection.update_one(
            {"_id": app_doc["_id"]},
            {"$set": {"status": "running", "deploy_stage": "running"}}
        )
        return {
            "success": True,
            "app_id": app_id,
            "name": name,
            "url": app_doc["deployment_url"],
            "message": f"App '{name}' created and deployed successfully"
        }
    except Exception as e:
        error_msg = str(e)
        await apps_collection.update_one(
            {"_id": app_doc["_id"]},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg}}
        )
        return {"error": f"Deployment failed: {error_msg}", "app_id": app_id}


async def _update_app(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Update an existing app's code and redeploy."""
    app_id = input_data.get("app_id")
    code = input_data.get("code")
    files = input_data.get("files")
    new_name = input_data.get("name")

    if not app_id:
        return {"error": "app_id is required"}

    # Find the app
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    mode = app.get("mode", "single")
    update_data = {}

    if new_name:
        update_data["name"] = new_name

    # Handle code/files update based on mode
    if mode == "multi":
        if files:
            is_valid, error_msg, error_line, error_file = validate_multifile(
                files, app.get("entrypoint", "app.py")
            )
            if not is_valid:
                return {"error": f"Code validation failed in {error_file} line {error_line}: {error_msg}"}
            update_data["files"] = files
    else:
        if code:
            is_valid, error_msg, error_line = validate_code(code)
            if not is_valid:
                return {"error": f"Code validation failed at line {error_line}: {error_msg}"}
            update_data["code"] = code

    if not update_data:
        return {"error": "No updates provided (need code, files, or name)"}

    # Update and redeploy
    update_data["status"] = "deploying"
    update_data["deploy_stage"] = "deploying"
    update_data["last_deploy_at"] = datetime.utcnow()

    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": update_data}
    )

    updated_app = await apps_collection.find_one({"_id": app["_id"]})

    try:
        await update_app_deployment(updated_app, user)

        # Update deployed code/files tracking
        success_update = {"status": "running", "deploy_stage": "running"}
        if mode == "multi" and files:
            success_update["deployed_files"] = files
            success_update["draft_files"] = None
        elif code:
            success_update["deployed_code"] = code
            success_update["draft_code"] = None
        success_update["deployed_at"] = datetime.utcnow()

        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": success_update}
        )

        return {
            "success": True,
            "app_id": app_id,
            "url": app["deployment_url"],
            "message": f"App '{updated_app['name']}' updated and redeployed successfully"
        }
    except Exception as e:
        error_msg = str(e)
        await apps_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg}}
        )
        return {"error": f"Deployment failed: {error_msg}"}


async def _get_app(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Get details about an app."""
    app_id = input_data.get("app_id")
    if not app_id:
        return {"error": "app_id is required"}

    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    mode = app.get("mode", "single")
    result = {
        "app_id": app["app_id"],
        "name": app["name"],
        "status": app["status"],
        "url": app["deployment_url"],
        "mode": mode,
        "framework": app.get("framework"),
        "created_at": app["created_at"].isoformat(),
        "last_deploy_at": app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None,
        "error_message": app.get("error_message"),
        "database_id": app.get("database_id")
    }

    if mode == "multi":
        result["files"] = app.get("files", {})
        result["entrypoint"] = app.get("entrypoint", "app.py")
    else:
        result["code"] = app.get("code", "")

    return result


async def _get_app_logs(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Get logs from an app's deployment."""
    app_id = input_data.get("app_id")
    tail_lines = input_data.get("tail_lines", 50)

    if not app_id:
        return {"error": "app_id is required"}

    # Verify user owns the app
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    try:
        result = await get_pod_logs(app_id, tail_lines)
        logs = result.get("logs", [])

        # Format logs as simple text
        log_lines = [log.get("message", "") for log in logs]

        return {
            "app_id": app_id,
            "pod_name": result.get("pod_name"),
            "logs": log_lines,
            "truncated": result.get("truncated", False),
            "error": result.get("error")
        }
    except Exception as e:
        return {"error": f"Failed to get logs: {str(e)}"}


async def _list_apps(user: dict) -> Dict[str, Any]:
    """List all user's apps."""
    apps = []
    async for app in apps_collection.find({"user_id": user["_id"], "status": {"$ne": "deleted"}}):
        apps.append({
            "app_id": app["app_id"],
            "name": app["name"],
            "status": app["status"],
            "url": app["deployment_url"],
            "mode": app.get("mode", "single"),
            "framework": app.get("framework"),
            "created_at": app["created_at"].isoformat()
        })

    return {"apps": apps, "count": len(apps)}


async def _delete_app(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Delete an app."""
    app_id = input_data.get("app_id")
    if not app_id:
        return {"error": "app_id is required"}

    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    # Delete from Kubernetes
    try:
        await delete_app_deployment(app, user)
    except Exception as e:
        logger.error(f"Error deleting deployment for {app_id}: {e}")

    # Mark as deleted
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {"status": "deleted"}}
    )

    return {
        "success": True,
        "app_id": app_id,
        "message": f"App '{app['name']}' deleted successfully"
    }


async def _list_databases(user: dict) -> Dict[str, Any]:
    """List user's available databases."""
    databases = user.get("databases", [])

    return {
        "databases": [
            {
                "id": db["id"],
                "name": db.get("name", db["id"]),
                "created_at": db.get("created_at").isoformat() if db.get("created_at") else None
            }
            for db in databases
        ],
        "count": len(databases)
    }
