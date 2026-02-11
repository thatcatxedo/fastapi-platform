"""
Utility functions for FastAPI Platform
Shared helper functions for error handling and formatting
"""
import base64
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId, Decimal128


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


def serialize_mongo_doc(doc: Any) -> Any:
    """
    Recursively convert a MongoDB document to a JSON-serializable dict.

    Handles: ObjectId -> str, datetime -> ISO str, bytes -> base64 str,
    Decimal128 -> str, and nested dicts/lists.
    """
    if isinstance(doc, dict):
        return {k: serialize_mongo_doc(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    if isinstance(doc, bytes):
        return base64.b64encode(doc).decode("ascii")
    if isinstance(doc, Decimal128):
        return str(doc)
    return doc
