"""
Kubernetes API client initialization
"""
from kubernetes import client as k8s_client
import logging

logger = logging.getLogger(__name__)

# Kubernetes API clients
try:
    from kubernetes import config as k8s_config
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    apps_v1 = k8s_client.AppsV1Api()
    core_v1 = k8s_client.CoreV1Api()
    custom_objects = k8s_client.CustomObjectsApi()
except Exception as e:
    logger.error(f"Failed to initialize Kubernetes client: {e}")
    apps_v1 = None
    core_v1 = None
    custom_objects = None
