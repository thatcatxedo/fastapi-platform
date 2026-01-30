"""
Kubernetes deployment management for user apps
"""
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
import os
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

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

from config import PLATFORM_NAMESPACE, APP_DOMAIN

RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
MONGO_VIEWER_IMAGE = os.getenv("MONGO_VIEWER_IMAGE", "mongo-express:latest")
MONGO_VIEWER_PORT = int(os.getenv("MONGO_VIEWER_PORT", "8081"))

def get_user_mongo_uri_legacy(user_id: str) -> str:
    """
    DEPRECATED: Construct per-user MongoDB URI using shared platform credentials.
    This is insecure and only used for backwards compatibility during migration.
    Use get_user_mongo_uri_secure() for new deployments.
    """
    from config import MONGO_URI
    base_uri = MONGO_URI if not MONGO_URI.endswith("/fastapi_platform_db") else MONGO_URI.replace("/fastapi_platform_db", "") + "/fastapi_platform_db"
    parsed = urlparse(base_uri)
    user_db_path = f"/user_{user_id}"
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        user_db_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def get_user_mongo_uri_secure(user_id: str, user: dict) -> str:
    """
    Construct per-user MongoDB URI with user-specific credentials.
    
    Args:
        user_id: Platform user ID
        user: User document containing mongo_password_encrypted
        
    Returns:
        MongoDB URI with per-user credentials, or legacy URI if credentials not available
    """
    from urllib.parse import quote_plus
    
    encrypted_password = user.get("mongo_password_encrypted")
    if not encrypted_password:
        # Fallback to legacy for users without MongoDB credentials
        logger.warning(f"User {user_id} has no MongoDB credentials, using legacy URI")
        return get_user_mongo_uri_legacy(user_id)
    
    try:
        from mongo_users import decrypt_password, get_mongo_username
        
        password = decrypt_password(encrypted_password)
        username = get_mongo_username(user_id)
        db_name = f"user_{user_id}"
        
        from config import MONGO_URI
        base_uri = MONGO_URI if not MONGO_URI.endswith("/fastapi_platform_db") else MONGO_URI.replace("/fastapi_platform_db", "") + "/fastapi_platform_db"
        parsed = urlparse(base_uri)
        
        # URL-encode username and password for safety
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)
        
        # Determine host:port
        hostname = parsed.hostname or "localhost"
        port = parsed.port or 27017
        
        # Build new URI with user credentials
        netloc = f"{encoded_username}:{encoded_password}@{hostname}:{port}"

        # Set authSource=admin (user is created in admin db)
        # Must replace any existing authSource since base URI may have different value
        from urllib.parse import parse_qs, urlencode
        query_params = parse_qs(parsed.query)
        query_params['authSource'] = ['admin']  # Always use admin for per-user auth
        query = urlencode(query_params, doseq=True)

        return urlunparse((
            parsed.scheme,
            netloc,
            f"/{db_name}",
            parsed.params,
            query,
            parsed.fragment
        ))
    except Exception as e:
        logger.error(f"Failed to build secure MongoDB URI for user {user_id}: {e}")
        # Fallback to legacy if decryption fails
        return get_user_mongo_uri_legacy(user_id)

def get_app_labels(user_id: str, app_id: str) -> dict:
    """Get standard labels for app resources"""
    return {
        "app": "user-fastapi-app",
        "user-id": str(user_id),
        "app-id": app_id,
        "managed-by": "fastapi-platform"
    }

def get_viewer_labels(user_id: str) -> dict:
    """Get standard labels for mongo viewer resources"""
    return {
        "app": "mongo-viewer",
        "user-id": str(user_id),
        "managed-by": "fastapi-platform"
    }

def get_viewer_name(user_id: str) -> str:
    return f"mongo-viewer-{user_id}"

async def create_mongo_viewer_deployment(user_id: str, user: dict, username: str, password: str):
    """Create Deployment for per-user MongoDB viewer"""
    if not apps_v1:
        raise Exception("Kubernetes client not available")

    deployment_name = get_viewer_name(user_id)

    # Using subdomain routing - no base URL prefix needed
    # Use per-user MongoDB credentials for secure access
    mongo_uri = get_user_mongo_uri_secure(user_id, user)
    env_list = [
        k8s_client.V1EnvVar(name="ME_CONFIG_MONGODB_URL", value=mongo_uri),
        k8s_client.V1EnvVar(name="ME_CONFIG_MONGODB_ENABLE_ADMIN", value="false"),
        k8s_client.V1EnvVar(name="ME_CONFIG_BASICAUTH_USERNAME", value=username),
        k8s_client.V1EnvVar(name="ME_CONFIG_BASICAUTH_PASSWORD", value=password),
    ]

    container = k8s_client.V1Container(
        name="mongo-express",
        image=MONGO_VIEWER_IMAGE,
        ports=[k8s_client.V1ContainerPort(container_port=MONGO_VIEWER_PORT, name="http")],
        env=env_list,
        resources=k8s_client.V1ResourceRequirements(
            requests={"memory": "32Mi", "cpu": "25m"},
            limits={"memory": "128Mi", "cpu": "200m"}
        )
    )

    pod_template = k8s_client.V1PodTemplateSpec(
        metadata=k8s_client.V1ObjectMeta(
            labels=get_viewer_labels(user_id)
        ),
        spec=k8s_client.V1PodSpec(
            containers=[container],
            image_pull_secrets=[k8s_client.V1LocalObjectReference(name="ghcr-auth")]
        )
    )

    deployment_spec = k8s_client.V1DeploymentSpec(
        replicas=1,
        selector=k8s_client.V1LabelSelector(
            match_labels=get_viewer_labels(user_id)
        ),
        template=pod_template
    )

    deployment = k8s_client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=deployment_name,
            namespace=PLATFORM_NAMESPACE,
            labels=get_viewer_labels(user_id)
        ),
        spec=deployment_spec
    )

    try:
        apps_v1.create_namespaced_deployment(
            namespace=PLATFORM_NAMESPACE,
            body=deployment
        )
        logger.info(f"Created mongo viewer Deployment for user {user_id}")
    except ApiException as e:
        if e.status == 409:
            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=PLATFORM_NAMESPACE,
                body=deployment
            )
            logger.info(f"Updated mongo viewer Deployment for user {user_id}")
        else:
            raise

async def create_mongo_viewer_service(user_id: str):
    """Create Service for per-user MongoDB viewer"""
    if not core_v1:
        raise Exception("Kubernetes client not available")

    service_name = get_viewer_name(user_id)

    service = k8s_client.V1Service(
        metadata=k8s_client.V1ObjectMeta(
            name=service_name,
            namespace=PLATFORM_NAMESPACE,
            labels=get_viewer_labels(user_id)
        ),
        spec=k8s_client.V1ServiceSpec(
            selector=get_viewer_labels(user_id),
            ports=[
                k8s_client.V1ServicePort(
                    port=80,
                    target_port=MONGO_VIEWER_PORT,
                    name="http"
                )
            ]
        )
    )

    try:
        core_v1.create_namespaced_service(
            namespace=PLATFORM_NAMESPACE,
            body=service
        )
        logger.info(f"Created mongo viewer Service for user {user_id}")
    except ApiException as e:
        if e.status == 409:
            core_v1.patch_namespaced_service(
                name=service_name,
                namespace=PLATFORM_NAMESPACE,
                body=service
            )
            logger.info(f"Updated mongo viewer Service for user {user_id}")
        else:
            raise

async def create_mongo_viewer_ingress_route(user_id: str):
    """Create Traefik IngressRoute for per-user MongoDB viewer with subdomain routing"""
    if not custom_objects:
        raise Exception("Kubernetes client not available")

    ingress_name = get_viewer_name(user_id)
    viewer_hostname = f"mongo-{user_id}.{APP_DOMAIN}"

    ingress_route = {
        "apiVersion": "traefik.io/v1alpha1",
        "kind": "IngressRoute",
        "metadata": {
            "name": ingress_name,
            "namespace": PLATFORM_NAMESPACE,
            "labels": get_viewer_labels(user_id)
        },
        "spec": {
            "entryPoints": ["web"],
            "routes": [
                {
                    "match": f"Host(`{viewer_hostname}`)",
                    "kind": "Rule",
                    "services": [
                        {
                            "name": get_viewer_name(user_id),
                            "port": 80
                        }
                    ]
                }
            ]
        }
    }

    try:
        custom_objects.create_namespaced_custom_object(
            group="traefik.io",
            version="v1alpha1",
            namespace=PLATFORM_NAMESPACE,
            plural="ingressroutes",
            body=ingress_route
        )
        logger.info(f"Created mongo viewer IngressRoute for user {user_id}")
    except ApiException as e:
        if e.status == 409:
            custom_objects.patch_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=PLATFORM_NAMESPACE,
                plural="ingressroutes",
                name=ingress_name,
                body=ingress_route
            )
            logger.info(f"Updated mongo viewer IngressRoute for user {user_id}")
        else:
            raise

async def create_mongo_viewer_resources(user_id: str, user: dict, username: str, password: str):
    """Create all Kubernetes resources for a per-user MongoDB viewer"""
    try:
        await create_mongo_viewer_deployment(user_id, user, username, password)
        await create_mongo_viewer_service(user_id)
        await create_mongo_viewer_ingress_route(user_id)
    except Exception as e:
        logger.error(f"Failed to create mongo viewer resources for user {user_id}: {e}")
        raise

async def get_mongo_viewer_status(user_id: str) -> Optional[dict]:
    """Get mongo viewer deployment status from Kubernetes"""
    if not apps_v1 or not core_v1:
        return None

    deployment_name = get_viewer_name(user_id)
    label_selector = ",".join([f"{k}={v}" for k, v in get_viewer_labels(user_id).items()])

    try:
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name,
            namespace=PLATFORM_NAMESPACE
        )

        pods = core_v1.list_namespaced_pod(
            namespace=PLATFORM_NAMESPACE,
            label_selector=label_selector
        )

        pod_status = None
        if pods.items:
            pod = pods.items[0]
            pod_status = pod.status.phase
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if not cs.ready:
                        pod_status = "NotReady"
                        break

        ready_replicas = deployment.status.ready_replicas or 0
        desired_replicas = deployment.spec.replicas or 0

        return {
            "ready": ready_replicas >= desired_replicas and desired_replicas > 0,
            "pod_status": pod_status
        }
    except ApiException as e:
        if e.status == 404:
            return {"ready": False, "pod_status": "NotFound"}
        return None
    except Exception as e:
        logger.error(f"Error getting mongo viewer status: {e}")
        return None

async def create_configmap(app_doc: dict, user: dict):
    """Create ConfigMap with user code"""
    if not core_v1:
        raise Exception("Kubernetes client not available")
    
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    
    configmap = k8s_client.V1ConfigMap(
        metadata=k8s_client.V1ObjectMeta(
            name=f"app-{app_id}-code",
            namespace=PLATFORM_NAMESPACE,
            labels=get_app_labels(user_id, app_id)
        ),
        data={
            "user_code.py": app_doc["code"]
        }
    )
    
    try:
        core_v1.create_namespaced_config_map(
            namespace=PLATFORM_NAMESPACE,
            body=configmap
        )
        logger.info(f"Created ConfigMap for app {app_id}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            # Update instead
            core_v1.patch_namespaced_config_map(
                name=f"app-{app_id}-code",
                namespace=PLATFORM_NAMESPACE,
                body=configmap
            )
            logger.info(f"Updated ConfigMap for app {app_id}")
        else:
            raise

async def create_deployment(app_doc: dict, user: dict):
    """Create Deployment for user app"""
    if not apps_v1:
        raise Exception("Kubernetes client not available")
    
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    deployment_name = f"app-{app_id}"
    
    # Build environment variables list with per-user MongoDB credentials
    mongo_uri = get_user_mongo_uri_secure(user_id, user)
    env_list = [
        k8s_client.V1EnvVar(name="CODE_PATH", value="/app/user_code.py"),
        k8s_client.V1EnvVar(name="PLATFORM_MONGO_URI", value=mongo_uri)
    ]
    # Add user-defined env vars
    if app_doc.get("env_vars"):
        for key, value in app_doc["env_vars"].items():
            env_list.append(k8s_client.V1EnvVar(name=key, value=str(value)))

    # Container spec
    container = k8s_client.V1Container(
        name="runner",
        image=RUNNER_IMAGE,
        ports=[k8s_client.V1ContainerPort(container_port=8000, name="http")],
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="code",
                mount_path="/app/user_code.py",
                sub_path="user_code.py"
            )
        ],
        env=env_list,
        resources=k8s_client.V1ResourceRequirements(
            requests={"memory": "64Mi", "cpu": "50m"},
            limits={"memory": "128Mi", "cpu": "250m"}
        ),
        liveness_probe=k8s_client.V1Probe(
            http_get=k8s_client.V1HTTPGetAction(
                path="/health",
                port=8000
            ),
            initial_delay_seconds=10,
            period_seconds=30
        ),
        readiness_probe=k8s_client.V1Probe(
            http_get=k8s_client.V1HTTPGetAction(
                path="/health",
                port=8000
            ),
            initial_delay_seconds=5,
            period_seconds=10
        )
    )
    
    # Volume with ConfigMap
    volume = k8s_client.V1Volume(
        name="code",
        config_map=k8s_client.V1ConfigMapVolumeSource(
            name=f"app-{app_id}-code"
        )
    )
    
    # Pod template
    pod_template = k8s_client.V1PodTemplateSpec(
        metadata=k8s_client.V1ObjectMeta(
            labels=get_app_labels(user_id, app_id)
        ),
        spec=k8s_client.V1PodSpec(
            containers=[container],
            volumes=[volume],
            image_pull_secrets=[k8s_client.V1LocalObjectReference(name="ghcr-auth")]
        )
    )
    
    # Deployment spec
    deployment_spec = k8s_client.V1DeploymentSpec(
        replicas=1,
        selector=k8s_client.V1LabelSelector(
            match_labels=get_app_labels(user_id, app_id)
        ),
        template=pod_template
    )
    
    # Deployment
    deployment = k8s_client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=k8s_client.V1ObjectMeta(
            name=deployment_name,
            namespace=PLATFORM_NAMESPACE,
            labels=get_app_labels(user_id, app_id)
        ),
        spec=deployment_spec
    )
    
    try:
        apps_v1.create_namespaced_deployment(
            namespace=PLATFORM_NAMESPACE,
            body=deployment
        )
        logger.info(f"Created Deployment for app {app_id}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            # Update instead
            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=PLATFORM_NAMESPACE,
                body=deployment
            )
            logger.info(f"Updated Deployment for app {app_id}")
        else:
            raise

async def create_service(app_doc: dict, user: dict):
    """Create Service for user app"""
    if not core_v1:
        raise Exception("Kubernetes client not available")
    
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    service_name = f"app-{app_id}"
    
    service = k8s_client.V1Service(
        metadata=k8s_client.V1ObjectMeta(
            name=service_name,
            namespace=PLATFORM_NAMESPACE,
            labels=get_app_labels(user_id, app_id)
        ),
        spec=k8s_client.V1ServiceSpec(
            selector=get_app_labels(user_id, app_id),
            ports=[
                k8s_client.V1ServicePort(
                    port=80,
                    target_port=8000,
                    name="http"
                )
            ]
        )
    )
    
    try:
        core_v1.create_namespaced_service(
            namespace=PLATFORM_NAMESPACE,
            body=service
        )
        logger.info(f"Created Service for app {app_id}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            # Update instead
            core_v1.patch_namespaced_service(
                name=service_name,
                namespace=PLATFORM_NAMESPACE,
                body=service
            )
            logger.info(f"Updated Service for app {app_id}")
        else:
            raise

async def create_ingress_route(app_doc: dict, user: dict):
    """Create Traefik IngressRoute for user app using subdomain routing"""
    if not custom_objects:
        raise Exception("Kubernetes client not available")

    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    ingress_name = f"app-{app_id}"
    app_hostname = f"app-{app_id}.{APP_DOMAIN}"

    # Traefik IngressRoute CRD with subdomain-based routing
    ingress_route = {
        "apiVersion": "traefik.io/v1alpha1",
        "kind": "IngressRoute",
        "metadata": {
            "name": ingress_name,
            "namespace": PLATFORM_NAMESPACE,
            "labels": get_app_labels(user_id, app_id)
        },
        "spec": {
            "entryPoints": ["web"],
            "routes": [
                {
                    "match": f"Host(`{app_hostname}`)",
                    "kind": "Rule",
                    "services": [
                        {
                            "name": f"app-{app_id}",
                            "port": 80
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        custom_objects.create_namespaced_custom_object(
            group="traefik.io",
            version="v1alpha1",
            namespace=PLATFORM_NAMESPACE,
            plural="ingressroutes",
            body=ingress_route
        )
        logger.info(f"Created IngressRoute for app {app_id}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            # Update instead
            custom_objects.patch_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=PLATFORM_NAMESPACE,
                plural="ingressroutes",
                name=ingress_name,
                body=ingress_route
            )
            logger.info(f"Updated IngressRoute for app {app_id}")
        else:
            raise

async def create_app_deployment(app_doc: dict, user: dict):
    """Create all Kubernetes resources for an app"""
    try:
        await create_configmap(app_doc, user)
        await create_deployment(app_doc, user)
        await create_service(app_doc, user)
        await create_ingress_route(app_doc, user)
    except Exception as e:
        logger.error(f"Failed to create deployment for app {app_doc['app_id']}: {e}")
        raise

async def update_app_deployment(app_doc: dict, user: dict):
    """Update deployment with new code and/or env vars"""
    try:
        # Update ConfigMap with new code
        await create_configmap(app_doc, user)

        # Recreate deployment to pick up new code and env vars
        # This will patch the existing deployment with the updated spec
        await create_deployment(app_doc, user)

        logger.info(f"Updated Deployment for app {app_doc['app_id']}")
    except Exception as e:
        logger.error(f"Failed to update deployment for app {app_doc['app_id']}: {e}")
        raise

async def get_deployment_status(app_doc: dict, user: dict) -> Optional[dict]:
    """Get deployment status from Kubernetes"""
    if not apps_v1 or not core_v1:
        return None
    
    app_id = app_doc["app_id"]
    deployment_name = f"app-{app_id}"
    
    try:
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name,
            namespace=PLATFORM_NAMESPACE
        )
        
        # Get pod status
        pods = core_v1.list_namespaced_pod(
            namespace=PLATFORM_NAMESPACE,
            label_selector=f"app-id={app_id}"
        )
        
        pod_status = None
        if pods.items:
            pod = pods.items[0]
            pod_status = pod.status.phase
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if not cs.ready:
                        pod_status = "NotReady"
                        break
        
        return {
            "ready": deployment.status.ready_replicas == deployment.spec.replicas,
            "pod_status": pod_status,
            "replicas": deployment.status.replicas,
            "ready_replicas": deployment.status.ready_replicas
        }
    except ApiException as e:
        if e.status == 404:
            return {"ready": False, "pod_status": "NotFound"}
        return None
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return None

async def delete_app_deployment(app_doc: dict, user: dict):
    """Delete all Kubernetes resources for an app"""
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    
    try:
        # Delete IngressRoute
        if custom_objects:
            try:
                custom_objects.delete_namespaced_custom_object(
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=PLATFORM_NAMESPACE,
                    plural="ingressroutes",
                    name=f"app-{app_id}"
                )
            except ApiException as e:
                if e.status != 404:
                    raise

        # Delete Service
        if core_v1:
            try:
                core_v1.delete_namespaced_service(
                    name=f"app-{app_id}",
                    namespace=PLATFORM_NAMESPACE
                )
            except ApiException as e:
                if e.status != 404:
                    raise
        
        # Delete Deployment
        if apps_v1:
            try:
                apps_v1.delete_namespaced_deployment(
                    name=f"app-{app_id}",
                    namespace=PLATFORM_NAMESPACE
                )
            except ApiException as e:
                if e.status != 404:
                    raise
        
        # Delete ConfigMap
        if core_v1:
            try:
                core_v1.delete_namespaced_config_map(
                    name=f"app-{app_id}-code",
                    namespace=PLATFORM_NAMESPACE
                )
            except ApiException as e:
                if e.status != 404:
                    raise
        
        logger.info(f"Deleted all resources for app {app_id}")
    except Exception as e:
        logger.error(f"Failed to delete deployment for app {app_id}: {e}")
        raise

async def delete_mongo_viewer_resources(user_id: str):
    """Delete all Kubernetes resources for a per-user MongoDB viewer"""
    viewer_name = get_viewer_name(user_id)

    try:
        if custom_objects:
            try:
                custom_objects.delete_namespaced_custom_object(
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=PLATFORM_NAMESPACE,
                    plural="ingressroutes",
                    name=viewer_name
                )
            except ApiException as e:
                if e.status != 404:
                    raise

        if core_v1:
            try:
                core_v1.delete_namespaced_service(
                    name=viewer_name,
                    namespace=PLATFORM_NAMESPACE
                )
            except ApiException as e:
                if e.status != 404:
                    raise

        if apps_v1:
            try:
                apps_v1.delete_namespaced_deployment(
                    name=viewer_name,
                    namespace=PLATFORM_NAMESPACE
                )
            except ApiException as e:
                if e.status != 404:
                    raise

        logger.info(f"Deleted mongo viewer resources for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to delete mongo viewer resources for user {user_id}: {e}")
        raise


def derive_deployment_phase(events: list) -> str:
    """Derive user-friendly deployment phase from K8s events"""
    reasons = {e.get("reason") for e in events if e.get("reason")}
    has_warning = any(e.get("type") == "Warning" for e in events)

    # Check for error conditions first
    error_reasons = {"Failed", "BackOff", "FailedScheduling", "FailedMount", "FailedCreate"}
    if reasons & error_reasons or has_warning:
        return "error"

    # Progress through deployment phases
    if "Started" in reasons:
        return "starting"
    if "Created" in reasons:
        return "creating"
    if "Pulled" in reasons:
        return "pulled"
    if "Pulling" in reasons:
        return "pulling"
    if "Scheduled" in reasons:
        return "scheduled"

    return "pending"


async def get_pod_logs(app_id: str, tail_lines: int = 100, since_seconds: int = None) -> dict:
    """Get pod logs for an app"""
    if not core_v1:
        return {"error": "Kubernetes client not available", "logs": [], "pod_name": None}

    try:
        # Find the pod for this app
        pods = core_v1.list_namespaced_pod(
            namespace=PLATFORM_NAMESPACE,
            label_selector=f"app-id={app_id}"
        )

        if not pods.items:
            return {"error": "No pod found", "logs": [], "pod_name": None}

        pod = pods.items[0]
        pod_name = pod.metadata.name

        # Check if pod is in a state where logs are available
        if pod.status.phase not in ["Running", "Succeeded", "Failed"]:
            return {
                "error": f"Pod is {pod.status.phase}, logs not available yet",
                "logs": [],
                "pod_name": pod_name
            }

        # Build kwargs for log request
        kwargs = {
            "name": pod_name,
            "namespace": PLATFORM_NAMESPACE,
            "container": "runner",
            "tail_lines": tail_lines,
            "timestamps": True
        }
        if since_seconds:
            kwargs["since_seconds"] = since_seconds

        log_output = core_v1.read_namespaced_pod_log(**kwargs)

        # Parse logs into structured format
        logs = []
        for line in log_output.strip().split('\n'):
            if line:
                # Kubernetes timestamps: 2024-01-15T10:30:00.123456789Z message
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    logs.append({"timestamp": parts[0], "message": parts[1]})
                else:
                    logs.append({"timestamp": None, "message": line})

        return {
            "logs": logs,
            "pod_name": pod_name,
            "error": None,
            "truncated": len(logs) >= tail_lines
        }
    except ApiException as e:
        if e.status == 404:
            return {"error": "Pod not found", "logs": [], "pod_name": None}
        logger.error(f"Error getting pod logs for app {app_id}: {e}")
        return {"error": str(e), "logs": [], "pod_name": None}
    except Exception as e:
        logger.error(f"Error getting pod logs for app {app_id}: {e}")
        return {"error": str(e), "logs": [], "pod_name": None}


async def get_app_events(app_id: str, limit: int = 50) -> dict:
    """Get K8s events for app resources"""
    if not core_v1:
        return {"events": [], "deployment_phase": "unknown", "error": "Kubernetes client not available"}

    try:
        # Get all events in namespace
        all_events = core_v1.list_namespaced_event(
            namespace=PLATFORM_NAMESPACE
        )

        # Filter events for this app's resources (Pod, Deployment, ReplicaSet containing app_id)
        app_events = []
        for event in all_events.items:
            obj_name = event.involved_object.name or ""
            if app_id in obj_name:
                # Use last_timestamp if available, otherwise first_timestamp, otherwise event_time
                timestamp = None
                if event.last_timestamp:
                    timestamp = event.last_timestamp.isoformat()
                elif event.first_timestamp:
                    timestamp = event.first_timestamp.isoformat()
                elif event.event_time:
                    timestamp = event.event_time.isoformat()
                else:
                    timestamp = ""

                app_events.append({
                    "timestamp": timestamp,
                    "type": event.type or "Normal",
                    "reason": event.reason or "",
                    "message": event.message or "",
                    "involved_object": f"{event.involved_object.kind}/{event.involved_object.name}",
                    "count": event.count or 1
                })

        # Sort by timestamp descending (most recent first)
        app_events.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        app_events = app_events[:limit]

        # Derive deployment phase from events
        deployment_phase = derive_deployment_phase(app_events)

        return {
            "events": app_events,
            "deployment_phase": deployment_phase,
            "error": None
        }
    except ApiException as e:
        logger.error(f"Error getting events for app {app_id}: {e}")
        return {"events": [], "deployment_phase": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error getting events for app {app_id}: {e}")
        return {"events": [], "deployment_phase": "error", "error": str(e)}
