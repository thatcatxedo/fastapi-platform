"""
Tool definitions for AI chat assistant.
Claude can use these tools to help users build and manage apps.
"""
import logging
from typing import Any, Dict, List, Optional
import secrets
import string
from datetime import datetime
import httpx
import re

from database import apps_collection, users_collection, templates_collection
from deployment import (
    create_app_deployment,
    delete_app_deployment,
    update_app_deployment,
    get_pod_logs,
    get_deployment_status
)
from validation import validate_code, validate_multifile, detect_framework_from_files
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
        "description": "Update an existing app's code, settings, or database connection and redeploy it.",
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
                },
                "database_id": {
                    "type": "string",
                    "description": "Database ID to connect (use 'default' for user's default database, or specific ID from list_databases)"
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
        "description": "Get recent logs from an app's deployment with automatic error parsing. Returns raw logs plus structured errors_detected array with type, message, and suggestion for each error found. Use has_errors to quickly check if problems exist, and error_summary for a one-line overview.",
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
    },
    {
        "name": "list_templates",
        "description": "List available app templates that can be used as reference or starting points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "enum": ["fastapi", "fasthtml", "all"],
                    "description": "Filter by framework (default: all)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_template_code",
        "description": "Get the full code of a template to use as reference when creating apps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template_name": {
                    "type": "string",
                    "description": "Name of the template to retrieve"
                }
            },
            "required": ["template_name"]
        }
    },
    {
        "name": "validate_code_only",
        "description": "Check if code would pass validation WITHOUT deploying. Use this to verify code before creating or updating apps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to validate (for single-file mode)"
                },
                "files": {
                    "type": "object",
                    "description": "Files to validate (for multi-file mode): {filename: code}",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": []
        }
    },
    {
        "name": "test_endpoint",
        "description": "Make an HTTP request to a deployed app to verify it works. Use after deploying to test endpoints.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to test"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method (default: GET)"
                },
                "path": {
                    "type": "string",
                    "description": "Endpoint path (e.g., '/todos', '/health')"
                },
                "body": {
                    "type": "object",
                    "description": "Request body for POST/PUT/PATCH requests"
                },
                "headers": {
                    "type": "object",
                    "description": "Additional headers to send",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["app_id", "path"]
        }
    },
    {
        "name": "diagnose_app",
        "description": "Analyze app health, check pod status, recent errors, and get suggested fixes. Use when an app is failing or behaving unexpectedly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "description": "The app_id to diagnose"
                }
            },
            "required": ["app_id"]
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
        elif name == "list_templates":
            return await _list_templates(input_data)
        elif name == "get_template_code":
            return await _get_template_code(input_data)
        elif name == "validate_code_only":
            return await _validate_code_only(input_data)
        elif name == "test_endpoint":
            return await _test_endpoint(input_data, user)
        elif name == "diagnose_app":
            return await _diagnose_app(input_data, user)
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
        if "app.py" not in files:
            return {"error": "Multi-file apps must include app.py as entrypoint"}
        if not framework:
            framework = detect_framework_from_files(files, "app.py")
        elif framework not in ("fastapi", "fasthtml"):
            return {"error": "framework must be 'fastapi' or 'fasthtml'"}
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
    """Update an existing app's code, settings, or database connection and redeploy."""
    app_id = input_data.get("app_id")
    code = input_data.get("code")
    files = input_data.get("files")
    new_name = input_data.get("name")
    database_id = input_data.get("database_id")

    if not app_id:
        return {"error": "app_id is required"}

    # Validate files structure early if provided
    if files is not None:
        if not isinstance(files, dict):
            return {"error": f"'files' must be a dict of {{filename: code}}, got {type(files).__name__}"}
        if files:
            # Check all values are strings (code content)
            for filename, content in files.items():
                if not isinstance(content, str):
                    return {"error": f"File content for '{filename}' must be a string, got {type(content).__name__}"}
            logger.info(f"update_app called with {len(files)} files: {list(files.keys())}")

    # Find the app
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    mode = app.get("mode", "single")
    update_data = {}

    if new_name:
        update_data["name"] = new_name

    # Handle database_id update
    if database_id is not None:
        # Validate database_id if provided
        if database_id:
            databases = user.get("databases", [])
            if not any(db["id"] == database_id for db in databases):
                return {"error": f"Database '{database_id}' not found. Use list_databases to see available databases."}
        update_data["database_id"] = database_id if database_id else None

    # Handle code/files update based on mode
    if mode == "multi":
        if files:
            # Merge new files with existing files for validation
            # This ensures imports between files work correctly
            existing_files = app.get("files", {})
            merged_files = {**existing_files, **files}  # New files override existing

            is_valid, error_msg, error_line, error_file = validate_multifile(
                merged_files, app.get("entrypoint", "app.py")
            )
            if not is_valid:
                return {"error": f"Code validation failed in {error_file or 'unknown'} line {error_line or '?'}: {error_msg}"}
            update_data["files"] = merged_files
            update_data["framework"] = detect_framework_from_files(
                merged_files, app.get("entrypoint", "app.py")
            )
    else:
        if code:
            is_valid, error_msg, error_line = validate_code(code)
            if not is_valid:
                return {"error": f"Code validation failed at line {error_line}: {error_msg}"}
            update_data["code"] = code
        # If files passed to single-file app, that's an error
        if files:
            return {"error": "Cannot pass 'files' to a single-file app. Use 'code' instead, or convert the app to multi-file mode."}

    if not update_data:
        return {"error": "No updates provided (need code, files, name, or database_id)"}

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
            success_update["deployed_files"] = update_data.get("files", files)
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
    """Get logs from an app's deployment with automatic error parsing."""
    from chat.log_errors import parse_errors

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

        # Parse errors from logs
        error_analysis = parse_errors(log_lines)

        return {
            "app_id": app_id,
            "pod_name": result.get("pod_name"),
            "logs": log_lines,
            "truncated": result.get("truncated", False),
            "error": result.get("error"),
            # Enhanced error context
            "errors_detected": error_analysis["errors_detected"],
            "has_errors": error_analysis["has_errors"],
            "error_summary": error_analysis["error_summary"],
            "traceback": error_analysis["traceback"]
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


async def _list_templates(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """List available app templates."""
    framework_filter = input_data.get("framework", "all")

    query = {"is_global": True}
    if framework_filter and framework_filter != "all":
        query["framework"] = framework_filter

    templates = []
    async for template in templates_collection.find(query).sort("name", 1):
        templates.append({
            "name": template["name"],
            "description": template.get("description", ""),
            "framework": template.get("framework"),
            "mode": template.get("mode", "single"),
            "complexity": template.get("complexity", "simple"),
            "tags": template.get("tags", [])
        })

    return {
        "templates": templates,
        "count": len(templates),
        "tip": "Use get_template_code to fetch the full code of a template as reference"
    }


async def _get_template_code(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get the full code of a template."""
    template_name = input_data.get("template_name")
    if not template_name:
        return {"error": "template_name is required"}

    # Search case-insensitive
    template = await templates_collection.find_one({
        "name": {"$regex": f"^{re.escape(template_name)}$", "$options": "i"},
        "is_global": True
    })

    if not template:
        # Try partial match
        template = await templates_collection.find_one({
            "name": {"$regex": re.escape(template_name), "$options": "i"},
            "is_global": True
        })

    if not template:
        return {"error": f"Template '{template_name}' not found. Use list_templates to see available templates."}

    result = {
        "name": template["name"],
        "description": template.get("description", ""),
        "framework": template.get("framework"),
        "mode": template.get("mode", "single")
    }

    if template.get("mode") == "multi":
        result["files"] = template.get("files", {})
        result["entrypoint"] = template.get("entrypoint", "app.py")
    else:
        result["code"] = template.get("code", "")

    return result


async def _validate_code_only(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate code without deploying."""
    code = input_data.get("code")
    files = input_data.get("files")

    if files:
        # Multi-file validation
        is_valid, error_msg, error_line, error_file = validate_multifile(files, "app.py")
        if is_valid:
            return {
                "valid": True,
                "message": "Code passes all validation checks",
                "mode": "multi",
                "file_count": len(files)
            }
        else:
            return {
                "valid": False,
                "error": error_msg,
                "line": error_line,
                "file": error_file,
                "mode": "multi"
            }
    elif code:
        # Single-file validation
        is_valid, error_msg, error_line = validate_code(code)
        if is_valid:
            return {
                "valid": True,
                "message": "Code passes all validation checks",
                "mode": "single"
            }
        else:
            return {
                "valid": False,
                "error": error_msg,
                "line": error_line,
                "mode": "single"
            }
    else:
        return {"error": "Either 'code' or 'files' is required"}


async def _test_endpoint(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Test an endpoint on a deployed app."""
    app_id = input_data.get("app_id")
    method = input_data.get("method", "GET").upper()
    path = input_data.get("path", "/")
    body = input_data.get("body")
    headers = input_data.get("headers", {})

    if not app_id:
        return {"error": "app_id is required"}

    # Verify user owns the app
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    if app.get("status") != "running":
        return {
            "error": f"App is not running (status: {app.get('status')}). Deploy it first or check diagnose_app for issues."
        }

    # Build URL
    base_url = app.get("deployment_url", f"https://app-{app_id}.{APP_DOMAIN}")
    if not path.startswith("/"):
        path = "/" + path
    url = f"{base_url}{path}"

    # Make the request
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            start_time = datetime.utcnow()

            request_kwargs = {
                "method": method,
                "url": url,
                "headers": {"Accept": "application/json", **headers}
            }
            if body and method in ("POST", "PUT", "PATCH"):
                request_kwargs["json"] = body

            response = await client.request(**request_kwargs)

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Try to parse JSON response
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text[:1000]  # Truncate long text

            return {
                "success": 200 <= response.status_code < 400,
                "status_code": response.status_code,
                "url": url,
                "method": method,
                "response": response_body,
                "latency_ms": round(latency_ms, 2),
                "headers": dict(response.headers)
            }

    except httpx.TimeoutException:
        return {"error": f"Request to {url} timed out (30s)"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {str(e)}"}


async def _diagnose_app(input_data: Dict[str, Any], user: dict) -> Dict[str, Any]:
    """Diagnose app health and suggest fixes."""
    app_id = input_data.get("app_id")

    if not app_id:
        return {"error": "app_id is required"}

    # Get app
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        return {"error": f"App '{app_id}' not found"}

    diagnosis = {
        "app_id": app_id,
        "name": app["name"],
        "status": app.get("status"),
        "url": app.get("deployment_url"),
        "last_deploy": app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None,
        "error_message": app.get("error_message"),
        "issues": [],
        "suggestions": []
    }

    # Get deployment status from K8s
    try:
        deployment_status = await get_deployment_status(app, user)
        if deployment_status:
            diagnosis["pod_status"] = deployment_status.get("pod_phase")
            diagnosis["ready_replicas"] = deployment_status.get("ready_replicas", 0)
            diagnosis["restart_count"] = deployment_status.get("restart_count", 0)

            # Analyze issues
            if deployment_status.get("pod_phase") == "CrashLoopBackOff":
                diagnosis["issues"].append("App is crash-looping (repeatedly failing and restarting)")
                diagnosis["suggestions"].append("Check logs with get_app_logs for the error message")

            if deployment_status.get("restart_count", 0) > 3:
                diagnosis["issues"].append(f"High restart count ({deployment_status['restart_count']})")
                diagnosis["suggestions"].append("App may have a startup error or resource issue")

            if deployment_status.get("ready_replicas", 0) == 0:
                diagnosis["issues"].append("No healthy pods running")
                diagnosis["suggestions"].append("App failed to start - check validation and logs")

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        diagnosis["deployment_check_error"] = str(e)

    # Get recent logs for error analysis using shared parser
    try:
        from chat.log_errors import parse_errors

        logs_result = await get_pod_logs(app_id, 30)
        logs = logs_result.get("logs", [])
        log_lines = [log.get("message", "") for log in logs]

        # Use shared error parser
        error_analysis = parse_errors(log_lines)

        if error_analysis["has_errors"]:
            # Add detected errors with suggestions to diagnosis
            diagnosis["detected_errors"] = [
                f"{e['message']} - {e['suggestion']}" if e.get('suggestion') else e['message']
                for e in error_analysis["errors_detected"]
            ]
            diagnosis["issues"].extend(diagnosis["detected_errors"])

        # Include traceback if found
        if error_analysis["traceback"]:
            diagnosis["traceback"] = error_analysis["traceback"]

        # Include recent error lines
        log_text = "\n".join(log_lines)
        error_lines = [l for l in log_text.split('\n') if 'error' in l.lower() or 'exception' in l.lower()][:5]
        if error_lines:
            diagnosis["recent_error_lines"] = error_lines

    except Exception as e:
        logger.error(f"Error analyzing logs: {e}")

    # Generate overall assessment
    if not diagnosis["issues"]:
        diagnosis["assessment"] = "App appears healthy"
    elif len(diagnosis["issues"]) == 1:
        diagnosis["assessment"] = f"Found 1 issue: {diagnosis['issues'][0]}"
    else:
        diagnosis["assessment"] = f"Found {len(diagnosis['issues'])} issues that need attention"

    return diagnosis
