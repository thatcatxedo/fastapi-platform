"""
Kubernetes deployment management for user apps
"""
from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException
import os
import logging
from datetime import datetime
from typing import Optional

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

PLATFORM_NAMESPACE = os.getenv("PLATFORM_NAMESPACE", "fastapi-platform")
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "platform.gofastapi.xyz")

def get_app_labels(user_id: str, app_id: str) -> dict:
    """Get standard labels for app resources"""
    return {
        "app": "user-fastapi-app",
        "user-id": str(user_id),
        "app-id": app_id,
        "managed-by": "fastapi-platform"
    }

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
    
    # Build environment variables list
    env_list = [
        k8s_client.V1EnvVar(name="CODE_PATH", value="/app/user_code.py")
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

async def create_middleware(app_doc: dict, user: dict):
    """Create Traefik Middleware to strip path prefix for user app"""
    if not custom_objects:
        raise Exception("Kubernetes client not available")
    
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    middleware_name = f"app-{app_id}-strip-prefix"
    path_prefix = f"/user/{user_id}/app/{app_id}"
    
    middleware = {
        "apiVersion": "traefik.io/v1alpha1",
        "kind": "Middleware",
        "metadata": {
            "name": middleware_name,
            "namespace": PLATFORM_NAMESPACE,
            "labels": get_app_labels(user_id, app_id)
        },
        "spec": {
            "stripPrefix": {
                "prefixes": [path_prefix]
            }
        }
    }
    
    try:
        custom_objects.create_namespaced_custom_object(
            group="traefik.io",
            version="v1alpha1",
            namespace=PLATFORM_NAMESPACE,
            plural="middlewares",
            body=middleware
        )
        logger.info(f"Created Middleware for app {app_id}")
    except ApiException as e:
        if e.status == 409:  # Already exists
            custom_objects.patch_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=PLATFORM_NAMESPACE,
                plural="middlewares",
                name=middleware_name,
                body=middleware
            )
            logger.info(f"Updated Middleware for app {app_id}")
        else:
            raise

async def create_ingress_route(app_doc: dict, user: dict):
    """Create Traefik IngressRoute for user app"""
    if not custom_objects:
        raise Exception("Kubernetes client not available")
    
    app_id = app_doc["app_id"]
    user_id = str(user["_id"])
    ingress_name = f"app-{app_id}"
    middleware_name = f"app-{app_id}-strip-prefix"
    
    # Traefik IngressRoute CRD
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
                    "match": f"Host(`{BASE_DOMAIN}`) && PathPrefix(`/user/{user_id}/app/{app_id}`)",
                    "kind": "Rule",
                    "services": [
                        {
                            "name": f"app-{app_id}",
                            "port": 80
                        }
                    ],
                    "middlewares": [
                        {
                            "name": middleware_name,
                            "namespace": PLATFORM_NAMESPACE
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
        await create_middleware(app_doc, user)
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
            
            # Delete Middleware
            try:
                custom_objects.delete_namespaced_custom_object(
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=PLATFORM_NAMESPACE,
                    plural="middlewares",
                    name=f"app-{app_id}-strip-prefix"
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
