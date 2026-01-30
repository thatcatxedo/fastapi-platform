[13 tools called]

Below is a full architecture review of the FastAPI platform app plus its cluster configuration, based on the current code and manifests. I’m in Ask mode so I’m only reporting and recommending; no changes made.

## Architecture Review

### System Overview (app)
- Backend is a FastAPI API that connects to MongoDB, issues JWTs, and orchestrates Kubernetes resources for user apps. It also seeds templates and enables permissive CORS. ```1:86:backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
...
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "platform.gofastapi.xyz")
APP_DOMAIN = os.getenv("APP_DOMAIN", "gatorlunch.com")  # Apps at app-{id}.{APP_DOMAIN}
...
app = FastAPI(title="FastAPI Learning Platform API", lifespan=lifespan)
...
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
...
PLATFORM_NAMESPACE = os.getenv("PLATFORM_NAMESPACE", "fastapi-platform")
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
INACTIVITY_THRESHOLD_HOURS = int(os.getenv("INACTIVITY_THRESHOLD_HOURS", "24"))
```
- Deployment orchestration is done via Kubernetes API clients; per-user Mongo DB URIs and per-app resource labels are created in `deployment.py`. ```31:67:backend/deployment.py
PLATFORM_NAMESPACE = os.getenv("PLATFORM_NAMESPACE", "fastapi-platform")
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "platform.gofastapi.xyz")
APP_DOMAIN = os.getenv("APP_DOMAIN", "gatorlunch.com")  # Apps at app-{id}.{APP_DOMAIN}
...
def get_user_mongo_uri(user_id: str) -> str:
    """Construct per-user MongoDB URI by replacing database name."""
    base_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/fastapi_platform_db")
    ...
    user_db_path = f"/user_{user_id}"
...
def get_app_labels(user_id: str, app_id: str) -> dict:
    """Get standard labels for app resources"""
    return {
        "app": "user-fastapi-app",
        "user-id": str(user_id),
        "app-id": app_id,
        "managed-by": "fastapi-platform"
    }
```
- Runner container loads and `exec`’s user code to build a FastAPI app; adds `/health` and patches Swagger UI to match routing. ```1:133:runner/entrypoint.py
CODE_PATH = os.getenv("CODE_PATH", "/app/user_code.py")
...
with open(CODE_PATH, 'r') as f:
    code = f.read()
...
exec(compile(code, CODE_PATH, 'exec'), user_globals)
...
app = add_health_wrapper(app)
...
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### System Overview (cluster)
- Platform ingress routes forward `/api` to backend and everything else to frontend; entrypoints are `web` only (HTTP). ```1:22:apps/fastapi-platform/ingressroutes.yaml
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`platform.gofastapi.xyz`) && PathPrefix(`/api`)
      kind: Rule
      services:
        - name: backend
          port: 80
    - match: Host(`platform.gofastapi.xyz`)
      kind: Rule
      services:
        - name: frontend
          port: 80
```
- Backend deployment is single-replica and uses a fixed `latest` runner image; Mongo URI is expected from `mongodb-external`. ```1:46:apps/fastapi-platform/backend-deployment.yaml
spec:
  replicas: 1
...
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: mongodb-external
              key: uri
...
        - name: RUNNER_IMAGE
          value: "ghcr.io/thatcatxedo/fastapi-platform-runner:latest"
```
- RBAC is cluster-wide for the backend service account in `homelab-cluster`. ```1:35:apps/fastapi-platform/rbac.yaml
kind: ClusterRole
metadata:
  name: fastapi-platform-backend
rules:
- apiGroups: [""]
  resources: ["configmaps", "services"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["traefik.io"]
  resources: ["ingressroutes", "middlewares"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```
- Traefik runs with `web` and `websecure` entrypoints, but the platform ingress uses only `web`. ```1:36:infrastructure/traefik/helmrelease.yaml
ports:
  web:
    port: 8000
    exposedPort: 80
  websecure:
    port: 8443
    exposedPort: 443
```
- Flux Kustomization for `apps-fastapi-platform` has no dependencies configured. ```157:176:clusters/homelab/apps.yaml
kind: Kustomization
metadata:
  name: apps-fastapi-platform
...
spec:
  # Dependencies removed - infrastructure is stable and apps will fail gracefully
  interval: 5m
...
  path: ./apps/fastapi-platform
```
- Manual secret sync is explicitly called out as a current gap. ```5:24:MANUAL_STEPS_FOR_AUTOMATION.md
When deploying a new app that uses MongoDB, the `mongodb-external` secret needs to exist in the app's namespace. Currently, this secret is not automatically created or synced across namespaces.
...
Backend pod had `CreateContainerConfigError` until secret was manually created
```

## Findings (ordered by severity)

### Critical
- **MongoDB secret distribution is manual**: New namespaces require `mongodb-external` to be copied manually, causing pod failures. This is documented as a known gap. ```5:24:MANUAL_STEPS_FOR_AUTOMATION.md
When deploying a new app that uses MongoDB, the `mongodb-external` secret needs to exist in the app's namespace. Currently, this secret is not automatically created or synced across namespaces.
...
Backend pod had `CreateContainerConfigError` until secret was manually created
```

### High
- **User code execution uses `exec` inside the runner**: This is intended, but it means platform safety depends on upstream validation and runtime isolation. Any validation gaps or dependency escapes become higher risk. ```29:58:runner/entrypoint.py
def execute_code(code: str):
    """Execute user code in isolated namespace"""
...
    exec(compile(code, CODE_PATH, 'exec'), user_globals)
```
- **No TLS on platform ingress**: Ingress for platform routes only uses `web`, while Traefik exposes `websecure`. If Cloudflared/Tunnel isn’t terminating TLS upstream, this is a real issue. ```1:12:apps/fastapi-platform/ingressroutes.yaml
spec:
  entryPoints:
    - web
```

### Medium
- **Backend is single replica**: No HA for API; any node failure or pod crash is a full outage. ```1:8:apps/fastapi-platform/backend-deployment.yaml
spec:
  replicas: 1
```
- **Runner image uses `latest`**: This prevents image automation and reproducibility for user pods. ```33:36:apps/fastapi-platform/backend-deployment.yaml
        - name: RUNNER_IMAGE
          value: "ghcr.io/thatcatxedo/fastapi-platform-runner:latest"
```
- **ClusterRole is cluster-wide**: Backend has cluster-level permissions; consider namespace-scoped Role if possible. ```8:21:apps/fastapi-platform/rbac.yaml
kind: ClusterRole
...
  resources: ["configmaps", "services"]
...
```

### Low
- **CORS is fully open**: Accepts all origins and headers; may be okay, but consider tightening for production. ```49:55:backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Flux Kustomization lacks infra dependencies**: This is intentional in your repo, but means apps can fail until infra is ready. ```157:167:clusters/homelab/apps.yaml
spec:
  # Dependencies removed - infrastructure is stable and apps will fail gracefully
```

## Recommendations

- **Automate MongoDB secret propagation**: Implement reflector or ExternalSecrets; you already documented this path. ```41:66:MANUAL_STEPS_FOR_AUTOMATION.md
Use a controller like Reflector ... automatically copy secrets to namespaces with specific labels.
...
reflector.v1.k8s.emberstack.com/reflects: "mongodb/mongodb-external"
```
- **Add TLS for the platform ingress**: Use `websecure` entrypoint + TLS configuration, or verify Cloudflared handles TLS end-to-end.
- **Automate runner image updates**: Switch to a tagged runner image and add image automation policy (like backend/frontend).
- **Reduce RBAC scope if feasible**: If all resources remain in `fastapi-platform`, you can likely use a namespace `Role` (as in `deploy/base/rbac.yaml`), not a cluster role. ```1:42:deploy/base/rbac.yaml
kind: Role
metadata:
  name: platform-backend
  namespace: fastapi-platform
...
```
- **Consider API HA**: Increase replicas and add readiness/liveness thresholds aligned with real startup.

## Assumptions / Open Questions
- Is TLS terminated by Cloudflared for the `platform.gofastapi.xyz` host? If yes, using `web` may still be acceptable; otherwise this is a strong gap.
- Is the runner image updated out-of-band? If not, image automation for the runner should be added.

If you want, I can drill deeper into specific paths (auth security, k8s resource creation, rate limits, logging/observability, or data protection) or map out a threat model.