# Opus Architecture Review

> **Last Updated**: January 2025
>
> **Status**: Generally accurate. Minor corrections noted inline.

---

# Full Architecture Review

## Executive Summary

This is a **multi-tenant FastAPI platform** where users write Python code in a web editor and deploy it as isolated Kubernetes applications. The architecture consists of two repositories:

1. **fastapi-platform** - The application (backend API, React frontend, runner container)
2. **fastapi-platform-cluster-foundation** - The infrastructure baseline (k3d, Traefik, MongoDB, Cloudflared)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL ACCESS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Cloudflare Tunnel (homelab)        │  Direct (local: nip.io domains)       │
│  *.gatorlunch.com / *.gofastapi.xyz │  *.127.0.0.1.nip.io                   │
└───────────────────────────────┬─────┴───────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                        TRAEFIK INGRESS CONTROLLER                            │
│  - IngressRoute CRD for routing                                              │
│  - Middleware CRD for path stripping                                         │
│  Routes:                                                                     │
│    platform.{domain}/api/*  → backend:80                                    │
│    platform.{domain}/*      → frontend:80                                   │
│    app-{id}.{domain}/*      → app-{id}:80 (user apps)                       │
│    mongo-{uid}.{domain}/*   → mongo-viewer-{uid}:8081                       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                      FASTAPI-PLATFORM NAMESPACE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────────────────┐   │
│  │  FRONTEND   │   │   BACKEND   │   │    USER APPS (per-deployment)   │   │
│  │ (React+Nginx)│   │  (FastAPI)  │   │  ┌──────────┐ ┌──────────┐      │   │
│  │             │   │             │   │  │app-abc123│ │app-xyz789│ ...  │   │
│  │ Monaco Editor│   │ K8s Client  │   │  │ (runner) │ │ (runner) │      │   │
│  │ Auth UI     │   │ JWT Auth    │   │  └──────────┘ └──────────┘      │   │
│  │ Dashboard   │   │ Code Valid. │   │                                  │   │
│  └─────────────┘   └──────┬──────┘   └──────────────────────────────────┘   │
│                           │                                                  │
│                           │ Creates dynamically:                             │
│                           │  - ConfigMap (user code)                         │
│                           │  - Deployment (runner image)                     │
│                           │  - Service (port 80→8000)                        │
│                           │  - IngressRoute (subdomain routing)              │
└───────────────────────────┼─────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────────────┐
│                           MONGODB NAMESPACE                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MongoDB StatefulSet (mongo:7.0)                                      │  │
│  │  - PVC: 8Gi                                                           │  │
│  │  - Databases:                                                         │  │
│  │    • fastapi_platform_db (platform data: users, apps, templates)     │  │
│  │    • user_{user_id} (per-user databases for app data isolation)      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Backend (`fastapi-platform/backend/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with 20+ endpoints for auth, apps, templates, viewer |
| `deployment.py` | Creates K8s resources: ConfigMap, Deployment, Service, IngressRoute |
| `cleanup.py` | Background task deletes inactive apps (24h) and viewers (48h) |
| `seed_templates.py` | Populates starter templates on startup |

**Key Features:**
- **JWT Authentication**: 7-day tokens, bcrypt password hashing
- **AST-based Code Validation**: Parses Python, validates imports, blocks dangerous patterns
- **Dynamic K8s Resource Creation**: Uses in-cluster client to create user app resources
- **Per-User MongoDB Databases**: Each user gets isolated `user_{user_id}` database
- **Activity Tracking**: Monitors last activity for cleanup scheduling

**Allowed Imports Whitelist:**
```python
fastapi, pydantic, typing, datetime, json, math, random, string,
collections, itertools, functools, operator, re, uuid, hashlib,
base64, urllib.parse, fasthtml, fastlite, os, sys, pathlib, time,
enum, dataclasses, decimal, html, http, copy, textwrap, calendar,
locale, secrets, statistics, pymongo, bson, jinja2
```

**Blocked Patterns:** `__import__`, `eval`, `exec`, `compile`, `open`, `subprocess`, `socket`, `os.system`

---

### 2. Frontend (`fastapi-platform/frontend/`)

| Page | Purpose |
|------|---------|
| `Dashboard.jsx` | App list, status badges, logs panel, viewer credentials |
| `Editor.jsx` | Monaco Editor, templates sidebar, env vars, deployment status timeline |
| `AppView.jsx` | Iframe preview of deployed app |
| `Database.jsx` | MongoDB stats, collections viewer, mongo-express integration |
| `Login/Signup.jsx` | Authentication forms |

**Tech Stack:**
- React 18.2 + React Router 6
- Monaco Editor (Python syntax, error highlighting, keyboard shortcuts)
- Vite 5 (dev server with API proxy)
- Dark theme CSS with CSS variables

---

### 3. Runner (`fastapi-platform/runner/`)

**Execution Flow:**
1. Reads user code from `/app/user_code.py` (mounted ConfigMap)
2. Executes in isolated namespace with pre-imported modules
3. Extracts `app = FastAPI()` instance
4. Injects `/health` endpoint for K8s probes
5. Patches Swagger UI for path prefix compatibility
6. Runs uvicorn on port 8000

**Pre-installed Packages:** FastAPI, uvicorn, pydantic, python-fasthtml, pymongo, jinja2

---

### 4. Cluster Foundation (`fastapi-platform-cluster-foundation/`)

**Bootstrap Scripts:**
| Script | Function |
|--------|----------|
| `01-install-k3d.sh` | Creates k3d cluster, disables built-in Traefik |
| `02-install-flux.sh` | Installs Flux CD controllers |
| `03-configure-sops.sh` | Sets up age encryption for secrets |
| `04-verify.sh` | Basic validation checks |

**Infrastructure Components:**

| Component | Type | Purpose |
|-----------|------|---------|
| Traefik | HelmRelease | Ingress controller with CRDs |
| MongoDB | StatefulSet | Platform database (8Gi PVC) |
| Cloudflared | Deployment | Public access via Cloudflare Tunnel |
| cert-manager | (placeholder) | Future TLS automation |

**Cluster Overlays:**

| Overlay | Domain | Cloudflared | Use Case |
|---------|--------|-------------|----------|
| `local` | `*.127.0.0.1.nip.io` | No | Local k3d development |
| `homelab` | `*.gatorlunch.com` | Yes | Production on home server |

---

## Deployment Flow

### User Code Deployment

```
User writes code in Monaco Editor
            │
            ▼
Backend validates (AST parse, import check, pattern scan)
            │
            ▼
Backend creates K8s resources:
  1. ConfigMap: app-{app_id}-code (contains user_code.py)
  2. Deployment: app-{app_id} (runner image, mounts ConfigMap)
  3. Service: app-{app_id} (port 80→8000)
  4. IngressRoute: app-{app_id}.{APP_DOMAIN}
            │
            ▼
Runner container starts, executes user code
            │
            ▼
App accessible at https://app-{app_id}.{domain}
```

### CI/CD Pipeline

```
Push to main
      │
      ▼
GitHub Actions builds 3 images in parallel:
  - ghcr.io/.../fastapi-platform-backend:ts-{timestamp}-{sha}
  - ghcr.io/.../fastapi-platform-frontend:ts-{timestamp}-{sha}
  - ghcr.io/.../fastapi-platform-runner:ts-{timestamp}-{sha}
      │
      ▼
Flux Image Automation (in homelab-cluster) detects new tags
      │
      ▼
Flux updates manifests and applies to cluster
```

---

## RBAC Configuration

The `platform-backend` ServiceAccount has permissions to:

| Resource | Verbs |
|----------|-------|
| `pods`, `services`, `configmaps` | get, list, watch, create, update, patch, delete |
| `pods/log` | get |
| `events` | get, list, watch |
| `deployments` | get, list, watch, create, update, patch, delete |
| `ingressroutes`, `middlewares` (Traefik CRDs) | get, list, watch, create, update, patch, delete |

---

## Data Models

**Users Collection:**
```javascript
{ username, email, password_hash, created_at }
```

**Apps Collection:**
```javascript
{ user_id, app_id, name, code, env_vars, status, deploy_stage,
  created_at, last_activity, last_deploy_at, deployment_url, error_message }
```

**Templates Collection:**
```javascript
{ name, description, code, complexity, is_global, user_id, tags }
```

**Viewer Instances Collection:**
```javascript
{ user_id, username, password_hash, url, created_at, last_access }
```

---

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | - | MongoDB connection string |
| `SECRET_KEY` | random | JWT signing key |
| `PLATFORM_NAMESPACE` | `fastapi-platform` | Target namespace |
| `RUNNER_IMAGE` | GHCR image | Runner container image |
| `BASE_DOMAIN` | `platform.gofastapi.xyz` | Platform domain |
| `APP_DOMAIN` | `gofastapi.xyz` | User app domain |
| `INACTIVITY_THRESHOLD_HOURS` | 24 | App cleanup threshold |

---

## Security Model

| Layer | Mechanism |
|-------|-----------|
| **Authentication** | JWT tokens (7-day expiry), bcrypt passwords |
| **Authorization** | Per-user app ownership, token validation on all endpoints |
| **Code Validation** | AST parsing, import whitelist, forbidden pattern detection |
| **Runtime Isolation** | Separate pods per user app, resource limits |
| **Data Isolation** | Per-user MongoDB databases (`user_{user_id}`) |
| **Network** | Traefik routing, no direct pod access |
| **Secrets** | SOPS encryption for cluster secrets |

---

## Observations & Recommendations

### Strengths

1. **Clean Separation of Concerns**: Foundation infrastructure is separate from application code
2. **Multi-Environment Support**: Local, homelab, and prod overlays with Kustomize
3. **GitOps Ready**: Flux-compatible image tagging, HelmReleases for infrastructure
4. **Robust Code Validation**: AST-based parsing prevents execution during validation
5. **Per-User Data Isolation**: Separate MongoDB databases per user

### Areas for Improvement

1. **No Horizontal Scaling**: Backend and frontend are single replica; consider HPA for production
2. **No Rate Limiting**: API endpoints lack rate limiting; could be added via Traefik middleware
3. **No Refresh Tokens**: JWT expires after 7 days with no refresh mechanism
4. **Resource Limits on User Apps**: Fixed at 64-128Mi memory; may need dynamic sizing
5. **No Pod Security Standards**: User app pods run without explicit security contexts
6. **Cleanup Error Handling**: Cleanup loop logs errors but doesn't retry failed deletions
7. **No Metrics/Monitoring**: No Prometheus metrics or alerting configured
8. **Frontend Token Storage**: Uses `localStorage` (vulnerable to XSS); consider httpOnly cookies

### Production Readiness Checklist

| Item | Status |
|------|--------|
| TLS termination | ✅ Via Cloudflare Tunnel |
| Secrets encryption | ✅ SOPS with age |
| Resource limits | ✅ On platform pods, user apps |
| Health checks | ✅ Liveness and readiness probes |
| Cleanup automation | ✅ Inactive app deletion |
| CI/CD pipeline | ✅ GitHub Actions + Flux |
| Multi-environment | ✅ local/homelab/prod overlays |
| Logging | ⚠️ Console only, no aggregation |
| Monitoring | ❌ Not configured |
| Backup strategy | ❌ Not documented |
| Pod Security | ⚠️ No explicit security contexts |

---

This architecture provides a solid foundation for a hobby/homelab deployment. For a production SaaS, you'd want to add observability, backups, pod security policies, and horizontal scaling.