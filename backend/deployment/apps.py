"""
Kubernetes deployment management for user apps
"""
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
import os
import logging
import hashlib
from typing import Optional

from config import PLATFORM_NAMESPACE, APP_DOMAIN
from .k8s_client import apps_v1, core_v1, custom_objects
from .helpers import get_user_mongo_uri_secure, create_or_update_resource, create_or_update_custom_object

logger = logging.getLogger(__name__)

RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")


def get_app_labels(user_id: str, app_id: str) -> dict:
    """Get standard labels for app resources"""
    return {
        "app": "user-fastapi-app",
        "user-id": str(user_id),
        "app-id": app_id,
        "managed-by": "fastapi-platform"
    }


def build_configmap_data(app_doc: dict) -> dict:
    """Build ConfigMap data from app document (single or multi-file)."""
    mode = app_doc.get("mode", "single")

    if mode == "multi":
        # Multi-file: each file becomes a ConfigMap key
        return app_doc.get("files", {})
    else:
        # Single-file: wrap in main.py for backwards compatibility
        return {"main.py": app_doc["code"]}


def compute_code_hash(app_doc: dict) -> str:
    """Compute hash of code for deployment rollout trigger."""
    mode = app_doc.get("mode", "single")

    if mode == "multi":
        # Hash all files sorted by name for consistency
        files = app_doc.get("files", {})
        content = "".join(f"{k}:{v}" for k, v in sorted(files.items()))
    else:
        content = app_doc.get("code", "")

    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def create_configmap(app_doc: dict, user: dict):
    """Create ConfigMap with user code (single or multi-file)"""
    if not core_v1:
        raise Exception("Kubernetes client not available")

    app_id = app_doc["app_id"]
    user_id = str(user["_id"])

    configmap_data = build_configmap_data(app_doc)

    configmap = k8s_client.V1ConfigMap(
        metadata=k8s_client.V1ObjectMeta(
            name=f"app-{app_id}-code",
            namespace=PLATFORM_NAMESPACE,
            labels=get_app_labels(user_id, app_id)
        ),
        data=configmap_data
    )

    create_or_update_resource(
        core_v1.create_namespaced_config_map,
        core_v1.patch_namespaced_config_map,
        f"app-{app_id}-code", configmap, f"ConfigMap for app {app_id}"
    )


async def create_deployment(app_doc: dict, user: dict):
    """Create Deployment for user app (single or multi-file)"""
    if not apps_v1:
        raise Exception("Kubernetes client not available")

    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    deployment_name = f"app-{app_id}"
    mode = app_doc.get("mode", "single")

    # Compute a hash of the code to use as a restart trigger
    # When code changes, this annotation changes, forcing a pod rollout
    code_hash = compute_code_hash(app_doc)

    # Determine CODE_PATH based on mode
    if mode == "multi":
        entrypoint = app_doc.get("entrypoint", "app.py")
        code_path = f"/app/{entrypoint}"
    else:
        code_path = "/app/main.py"

    # Build environment variables list with per-user MongoDB credentials
    mongo_uri = get_user_mongo_uri_secure(user_id, user)
    env_list = [
        k8s_client.V1EnvVar(name="CODE_PATH", value=code_path),
        k8s_client.V1EnvVar(name="PLATFORM_MONGO_URI", value=mongo_uri)
    ]
    # Add user-defined env vars
    if app_doc.get("env_vars"):
        for key, value in app_doc["env_vars"].items():
            env_list.append(k8s_client.V1EnvVar(name=key, value=str(value)))

    # Container spec - mount entire ConfigMap as directory
    container = k8s_client.V1Container(
        name="runner",
        image=RUNNER_IMAGE,
        ports=[k8s_client.V1ContainerPort(container_port=8000, name="http")],
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="code",
                mount_path="/app"
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
            labels=get_app_labels(user_id, app_id),
            annotations={
                # This annotation changes when code changes, forcing K8s to restart pods
                "platform.gofastapi.xyz/code-hash": code_hash
            }
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

    create_or_update_resource(
        apps_v1.create_namespaced_deployment,
        apps_v1.patch_namespaced_deployment,
        deployment_name, deployment, f"Deployment for app {app_id}"
    )


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

    create_or_update_resource(
        core_v1.create_namespaced_service,
        core_v1.patch_namespaced_service,
        service_name, service, f"Service for app {app_id}"
    )


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

    create_or_update_custom_object(
        ingress_name, ingress_route, f"IngressRoute for app {app_id}"
    )


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
