# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-tenant platform where users write FastAPI code in a web editor and deploy it as isolated Kubernetes applications. Each user app runs as a separate pod with code mounted via ConfigMap.

**Live at**: `platform.gofastapi.xyz`

## Development Commands

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
npm run dev      # Dev server on port 5173
npm run build    # Production build
```

### Runner (Docker image for user apps)
```bash
cd runner
docker build -t fastapi-platform-runner:latest .
```

## Architecture

### Components
- **backend/**: FastAPI API that handles auth, app CRUD, and dynamically creates K8s resources
- **frontend/**: React + Monaco Editor for code editing, deployed via nginx
- **runner/**: Pre-built container that executes user code from ConfigMap

### Key Backend Files
- `main.py` - API endpoints, code validation (AST-based), auth
- `deployment.py` - Creates K8s resources: ConfigMap, Deployment, Service, Traefik Middleware/IngressRoute
- `cleanup.py` - Deletes inactive apps after 24 hours
- `seed_templates.py` - Populates MongoDB with starter templates on startup

### Deployment Flow
When user deploys code:
1. Backend validates code (AST parsing, import whitelist, security checks)
2. Creates ConfigMap with user code
3. Creates Deployment using runner image (mounts ConfigMap at `/app/user_code.py`)
4. Creates Service (port 80 → 8000)
5. Creates Traefik Middleware (strips path prefix) + IngressRoute
6. App accessible at `platform.gofastapi.xyz/user/{user_id}/app/{app_id}`

### Runner Execution
`runner/entrypoint.py` reads `/app/user_code.py`, executes in isolated namespace, extracts `app = FastAPI()` instance, adds `/health` endpoint if missing, starts uvicorn.

## Cluster Requirements

See `docs/PLATFORM_CONTRACT.md` for full details:
- Kubernetes with Traefik + CRDs (`IngressRoute`, `Middleware`)
- MongoDB accessible at `MONGO_URI`
- Backend ServiceAccount needs RBAC to create Deployments, Services, ConfigMaps, and Traefik CRDs in `fastapi-platform` namespace
- Image pull secret `ghcr-auth` for runner images

## Environment Variables
- `MONGO_URI` - MongoDB connection string
- `SECRET_KEY` - JWT signing key
- `PLATFORM_NAMESPACE` - Target namespace (default: `fastapi-platform`)
- `RUNNER_IMAGE` - Runner container image
- `BASE_DOMAIN` - Platform domain (default: `platform.gofastapi.xyz`)
- `INACTIVITY_THRESHOLD_HOURS` - App cleanup threshold (default: 24)

## CI/CD

GitHub Actions (`.github/workflows/build.yaml`) builds and pushes images on push to `main`:
- Images tagged `ts-{timestamp}-{short_sha}` for Flux compatibility
- Registry: `ghcr.io/thatcatxedo/fastapi-platform-{backend,frontend,runner}`
- Flux Image Automation in homelab-cluster picks up new tags and updates deployments

## Related Repositories

- **homelab-cluster/**: GitOps repo with Flux, contains K8s manifests for deploying this platform
- **fastapi-platform-cluster-foundation/**: WIP cluster baseline setup (k3d, Traefik, MongoDB, SOPS)

## Kubectl Access

```bash
export KUBECONFIG=/Users/dbuck/.kube/configs/homelab-cluster-ruben/config
kubectl get pods -n fastapi-platform
kubectl logs -n fastapi-platform deployment/backend
```

## Code Validation Rules

User code is validated in `backend/main.py`:
- Must contain `app = FastAPI()`
- Allowed imports: fastapi, pydantic, typing, datetime, json, math, random, uuid, re, collections, itertools, functools, enum, dataclasses, decimal, hashlib, base64, urllib.parse, html, http
- Blocked patterns: `__import__`, `eval`, `exec`, `open`, `socket`, `subprocess`, `os.system`
