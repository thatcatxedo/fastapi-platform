"""
Configuration module for FastAPI Platform
Centralizes environment variables and Kubernetes client initialization
"""
import os
import secrets
import logging

logger = logging.getLogger(__name__)

# Environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "platform.gofastapi.xyz")
APP_DOMAIN = os.getenv("APP_DOMAIN", "gatorlunch.com")  # Apps at app-{id}.{APP_DOMAIN}

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Platform settings
PLATFORM_NAMESPACE = os.getenv("PLATFORM_NAMESPACE", "fastapi-platform")
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
INACTIVITY_THRESHOLD_HOURS = int(os.getenv("INACTIVITY_THRESHOLD_HOURS", "24"))

# n8n webhook settings for AI chat
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook")

# Kubernetes client setup
try:
    from kubernetes import client as k8s_client, config as k8s_config
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()
    k8s_apps_v1 = k8s_client.AppsV1Api()
    k8s_core_v1 = k8s_client.CoreV1Api()
    k8s_networking_v1 = k8s_client.NetworkingV1Api()
    k8s_custom_objects = k8s_client.CustomObjectsApi()
except Exception as e:
    logger.warning(f"Kubernetes client not available: {e}")
    k8s_apps_v1 = None
    k8s_core_v1 = None
    k8s_networking_v1 = None
    k8s_custom_objects = None
