"""
Utility functions for FastAPI Platform
Shared helper functions for error handling and formatting
"""
from typing import Optional


def error_payload(code: str, message: str, details: Optional[dict] = None) -> dict:
    """Create a standardized error response payload"""
    return {
        "code": code,
        "message": message,
        "details": details
    }


def friendly_k8s_error(error_msg: str) -> str:
    """Convert Kubernetes error messages to user-friendly messages"""
    if "Invalid value" in error_msg and "metadata.name" in error_msg:
        return "Invalid app name. Please use only lowercase letters, numbers, and hyphens."
    if "already exists" in error_msg.lower():
        return "An app with this name already exists. Please try again."
    if "Forbidden" in error_msg or "403" in error_msg:
        return "Permission denied. Please contact support."
    if "not found" in error_msg.lower():
        return "Resource not found. Please try again."
    if "message" in error_msg:
        try:
            import json
            error_dict = json.loads(error_msg.split("HTTP response body:")[-1].strip())
            if "message" in error_dict:
                return error_dict["message"]
        except Exception:
            pass
    return error_msg
