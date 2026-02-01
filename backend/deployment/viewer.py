"""
Kubernetes deployment management for MongoDB viewer
"""
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
import os
import logging
from typing import Optional

from config import PLATFORM_NAMESPACE, APP_DOMAIN
from .k8s_client import apps_v1, core_v1, custom_objects
from .helpers import get_user_mongo_uri_secure, create_or_update_resource, create_or_update_custom_object
from mongo_users import build_viewer_mongo_uri, decrypt_password

logger = logging.getLogger(__name__)

MONGO_VIEWER_IMAGE = os.getenv("MONGO_VIEWER_IMAGE", "mongo-express:latest")
MONGO_VIEWER_PORT = int(os.getenv("MONGO_VIEWER_PORT", "8081"))


def get_viewer_labels(user_id: str) -> dict:
    """Get standard labels for mongo viewer resources"""
    return {
        "app": "mongo-viewer",
        "user-id": str(user_id),
        "managed-by": "fastapi-platform"
    }


def get_viewer_name(user_id: str) -> str:
    return f"mongo-viewer-{user_id}"


async def create_mongo_viewer_deployment(
    user_id: str,
    user: dict,
    username: str,
    password: str,
    database_id: str = None,
    use_viewer_user: bool = False
):
    """Create Deployment for per-user MongoDB viewer

    Args:
        user_id: Platform user ID
        user: User document
        username: Basic auth username for web UI
        password: Basic auth password for web UI
        database_id: Specific database to connect to (deprecated)
        use_viewer_user: If True, use viewer user with access to all databases
    """
    if not apps_v1:
        raise Exception("Kubernetes client not available")

    deployment_name = get_viewer_name(user_id)

    # Determine MongoDB connection
    if use_viewer_user:
        # Use viewer user with access to all databases
        viewer_password_encrypted = user.get("viewer_password_encrypted")
        if not viewer_password_encrypted:
            raise Exception("Viewer user not configured for this user")
        viewer_mongo_password = decrypt_password(viewer_password_encrypted)
        # Get default database ID (first database the user has)
        databases = user.get("databases", [])
        default_db_id = databases[0]["id"] if databases else "default"
        mongo_uri = build_viewer_mongo_uri(user_id, viewer_mongo_password, default_db_id)
        # Disable admin mode - admin mode requires access to list ALL databases
        # User can still browse their database and manually navigate to others via URL
        enable_admin = "false"
    else:
        # Use database-specific credentials (legacy)
        mongo_uri = get_user_mongo_uri_secure(user_id, user, database_id=database_id)
        enable_admin = "false"

    env_list = [
        k8s_client.V1EnvVar(name="ME_CONFIG_MONGODB_URL", value=mongo_uri),
        k8s_client.V1EnvVar(name="ME_CONFIG_MONGODB_ENABLE_ADMIN", value=enable_admin),
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

    create_or_update_resource(
        apps_v1.create_namespaced_deployment,
        apps_v1.patch_namespaced_deployment,
        deployment_name, deployment, f"mongo viewer Deployment for user {user_id}"
    )


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

    create_or_update_resource(
        core_v1.create_namespaced_service,
        core_v1.patch_namespaced_service,
        service_name, service, f"mongo viewer Service for user {user_id}"
    )


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

    create_or_update_custom_object(
        ingress_name, ingress_route, f"mongo viewer IngressRoute for user {user_id}"
    )


async def create_mongo_viewer_resources(
    user_id: str,
    user: dict,
    username: str,
    password: str,
    database_id: str = None,
    use_viewer_user: bool = False
):
    """Create all Kubernetes resources for a per-user MongoDB viewer

    Args:
        user_id: Platform user ID
        user: User document
        username: Basic auth username for web UI
        password: Basic auth password for web UI
        database_id: Specific database to connect to (deprecated)
        use_viewer_user: If True, use viewer user with access to all databases
    """
    try:
        await create_mongo_viewer_deployment(
            user_id, user, username, password,
            database_id=database_id,
            use_viewer_user=use_viewer_user
        )
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
