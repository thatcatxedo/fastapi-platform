# FastAPI Learning Platform

A multi-tenant platform where users can write FastAPI/FastHTML code in a web editor and deploy it as isolated Kubernetes applications. Supports single-file and multi-file projects with per-user MongoDB databases.

## How It Works

### User Flow

1. **Sign Up / Login**: Users authenticate via JWT tokens stored in localStorage
2. **Write Code**: Users write FastAPI/FastHTML code in a Monaco Editor (VS Code editor in browser)
3. **Choose Mode**: Single-file for quick prototypes, multi-file for structured apps
4. **Deploy**: Code is validated, then deployed to Kubernetes as an isolated application
5. **Access**: Each app gets a unique subdomain: `https://app-{app_id}.{domain}` (e.g., `app-abc123.gatorlunch.com`)

### Deployment Process

When a user clicks "Deploy", the backend:

1. **Validates Code**:
   - Syntax check via Python AST parsing
   - Security check: ensures `app` instance exists (FastAPI or FastHTML)
   - Import whitelist: only allows safe imports (configurable by admin)
   - Multi-file: validates all files, enforces size limits (10 files, 100KB each, 500KB total)

2. **Creates Kubernetes Resources** (in order):
   - **ConfigMap**: Stores user code (single file or multiple files mounted at `/code`)
   - **Deployment**: Runs pre-built `fastapi-platform-runner` container
     - Container mounts ConfigMap at `/code`
     - `CODE_PATH` env var points to entrypoint (e.g., `/code/app.py`)
     - Runner adds `/code` to `sys.path` for multi-file imports
   - **Service**: Exposes the pod internally on port 80
   - **IngressRoute**: Routes subdomain traffic via Traefik (`app-{id}.{domain}`)

3. **Status Polling**: Frontend polls `/api/apps/{app_id}/deploy-status` to show deployment progress

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │────▶│   Frontend   │────▶│     Backend     │
│  (React)    │     │   (Nginx)    │     │    (FastAPI)    │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                    ┌─────▼─────┐          ┌──────▼──────┐         ┌─────▼─────┐
                    │  MongoDB  │          │ Kubernetes  │         │  Traefik   │
                    │  (Users,  │          │   (Pods,    │         │ (Ingress)  │
                    │   Apps)   │          │  Services)  │         │            │
                    └───────────┘          └──────┬──────┘         └─────┬──────┘
                                                    │                      │
                                          ┌─────────▼──────────┐          │
                                          │  User App Pods     │◀─────────┘
                                          │  (Runner Container)│
                                          │  - Reads code from │
                                          │    ConfigMap       │
                                          │  - Executes code   │
                                          │  - Serves FastAPI  │
                                          └────────────────────┘
```

### Components

**Frontend** (`frontend/`)
- React 18 + Vite
- Monaco Editor for code editing
- JWT-based authentication
- Real-time deployment status polling

**Backend** (`backend/`)
- FastAPI REST API
- MongoDB for user/app data
- Kubernetes Python client for dynamic resource creation
- Code validation and security checks

**Runner** (`runner/`)
- Pre-built Docker image with FastAPI, FastHTML, pymongo, jinja2, uvicorn
- Entrypoint script (`entrypoint.py`) that:
  1. Reads user code from `CODE_PATH` (mounted ConfigMap)
  2. Adds `/code` to `sys.path` for multi-file imports
  3. Executes code in isolated namespace
  4. Extracts `app` instance (FastAPI or FastHTML)
  5. Wraps app with `/health` endpoint for K8s probes
  6. Patches Swagger UI for relative OpenAPI paths
  7. Starts uvicorn server

### Security

- **Code Validation**: AST parsing blocks dangerous operations
- **Import Whitelist**: Only FastAPI ecosystem + safe stdlib
- **Resource Limits**: CPU (250m) and memory (128Mi) per pod
- **Isolation**: Each user app runs in separate pod with own ConfigMap
- **Authentication**: JWT tokens for API access

### Routing

User apps are accessible via subdomain routing:
```
https://app-{app_id}.{APP_DOMAIN}
```

Example: `https://app-abc123.gatorlunch.com`

Traefik routing flow:
1. Request hits Traefik IngressRoute matching `app-{id}.{domain}` host
2. Request forwarded directly to Service → Pod (no path stripping needed)
3. User's FastAPI/FastHTML app handles the request

### MongoDB Viewer

Each user can launch a MongoDB viewer (mongo-express) for their per-user database:
```
https://mongo-{user_id}.{APP_DOMAIN}
```

Example: `https://mongo-abc123.gatorlunch.com`

- Access is protected by per-user basic auth credentials
- Credentials are only returned on creation or rotation via:
  - `POST /api/viewer`
  - `POST /api/viewer/rotate`
- Viewer instances auto-expire after inactivity (`MONGO_VIEWER_TTL_HOURS`, default 48)

### Ephemeral Apps

- Apps auto-delete after 24 hours of inactivity
- Activity tracked via `/api/apps/{app_id}/activity` endpoint
- Cleanup job runs periodically in backend

## Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
export MONGO_URI="mongodb://localhost:27017"
export SECRET_KEY="dev-secret-key"
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Runner
```bash
cd runner
docker build -t fastapi-platform-runner:latest .
```

## Deployment

Deployed via GitOps (Flux) to Kubernetes cluster:

1. **CI/CD**: GitHub Actions workflow automatically builds and pushes images on every push to `main`
   - Images tagged with Flux-compatible format: `ts-{timestamp}-{short_sha}`
   - Pushes to GHCR: `ghcr.io/thatcatxedo/fastapi-platform-{component}`
2. **GitOps**: Flux Image Automation detects new tags and updates deployments automatically
3. **Manual**: Can also build/push manually if needed
4. Backend needs RBAC permissions to create resources in `fastapi-platform` namespace

Kustomize manifests live in `deploy/` and can be applied directly or consumed by
your GitOps repo. See `docs/DEPLOYMENT.md` for usage.

## Architecture Notes (Current State)

### What This Repo Is
- **Kubernetes-native platform**, not just a service deployed to Kubernetes.
- Backend **creates and manages Kubernetes resources directly** (Deployments, Services, ConfigMaps, Traefik CRDs).
- The cluster is part of the product, so the platform relies on a consistent cluster baseline.

### Current Assumptions and Coupling
- **Traefik CRDs** are required (`IngressRoute`, `Middleware`).
- **Backend RBAC** must allow creating resources in the `fastapi-platform` namespace.
- **MongoDB** must be available at `MONGO_URI`.
- **Image pull secret** for GHCR is expected (e.g., `ghcr-auth`).
- **Flux** (or equivalent GitOps) is assumed for platform deployment automation.
- Platform base domain assumed to be `platform.gofastapi.xyz`.

### Missing Pieces in This Repo
- ConfigMap/Secret examples for required env vars.
- Cleanup job scheduling (CronJob manifest).
- MongoDB deployment/backup guidance.
- Frontend readiness/liveness probes.

## Suggested Architecture Direction

### Split the Platform into 3 Layers
1. **Cluster Setup (new repo or component)**  
   Provision k3s, Traefik + CRDs, cert-manager, storage defaults, GitOps bootstrap.
2. **Platform Deployment (this repo)**  
   Own the manifests or Helm chart for backend/frontend/runner + RBAC.
3. **Platform Contract**  
   Document exactly what the cluster must provide (CRDs, namespaces, secrets, domain).

### Rationale
- The platform **depends on Kubernetes APIs at runtime**, so cluster setup should be explicit.
- A reproducible cluster baseline makes onboarding and future expansion much safer.
- Separating cluster setup from platform deployment clarifies responsibility and reduces drift.

## Development Environment Guidance

### Recommended Approach
- **Local k3s (k3d or Rancher Desktop)** is sufficient for daily development.
- Use a local domain like `platform.127.0.0.1.nip.io` or `platform.localtest.me` for host-based routing.
- Keep `BASE_DOMAIN` configurable for local vs. homelab.

### When You Need Homelab
- Only necessary for validating **public DNS + Cloudflare Tunnel + TLS** behavior.
- Daily feature work can be done fully local.

### Current Homelab Setup Notes
- Proxmox VM runs k3s.
- Cloudflare Tunnel routes `*.gofastapi.xyz` to Traefik on port 80.
- Additional dev domains are possible but require Cloudflare UI tunnel config.

## API Endpoints

- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login  
- `GET /api/auth/me` - Get current user
- `GET /api/apps` - List user's apps
- `POST /api/apps` - Create/deploy new app
- `GET /api/apps/{app_id}` - Get app details
- `POST /api/apps/validate` - Validate code (draft)
- `POST /api/apps/{app_id}/validate` - Validate code (existing app)
- `PUT /api/apps/{app_id}` - Update app code (redeploy)
- `DELETE /api/apps/{app_id}` - Delete app
- `GET /api/apps/{app_id}/status` - Get deployment status
- `GET /api/apps/{app_id}/deploy-status` - Get deploy stage and progress
