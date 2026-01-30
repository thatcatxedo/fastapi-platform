"""
Deployment package - Kubernetes resource management

Re-exports all public functions for backwards compatibility.
Existing imports like `from deployment import create_app_deployment` continue to work.
"""

# App deployment functions
from .apps import (
    create_app_deployment,
    update_app_deployment,
    delete_app_deployment,
    get_deployment_status,
    get_pod_logs,
    get_app_events,
)

# Viewer deployment functions
from .viewer import (
    create_mongo_viewer_resources,
    delete_mongo_viewer_resources,
    get_mongo_viewer_status,
)

# Helpers that may be used externally
from .helpers import (
    get_user_mongo_uri_secure,
    get_user_mongo_uri_legacy,
)

__all__ = [
    # Apps
    "create_app_deployment",
    "update_app_deployment",
    "delete_app_deployment",
    "get_deployment_status",
    "get_pod_logs",
    "get_app_events",
    # Viewer
    "create_mongo_viewer_resources",
    "delete_mongo_viewer_resources",
    "get_mongo_viewer_status",
    # Helpers
    "get_user_mongo_uri_secure",
    "get_user_mongo_uri_legacy",
]
