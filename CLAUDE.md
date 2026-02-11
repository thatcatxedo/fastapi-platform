# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-tenant platform where users write FastAPI/FastHTML code in a web editor and deploy it as isolated Kubernetes applications. Each user app runs as a separate pod with code mounted via ConfigMap. Supports single-file and multi-file projects.

**Live at**: `platform.gofastapi.xyz` (prod) | `platform.gatorlunch.com` (homelab)

## Quick Deploy

```bash
# Deploy to homelab environment (gatorlunch.com)
cp .env.example .env
# Edit .env if needed (defaults work for homelab)
./deploy.sh

# Teardown
./undeploy.sh
```

**Prerequisites**:
- cluster-foundation running (`../fastapi-platform-cluster-foundation/setup.sh`)
- `gh` CLI authenticated with `read:packages` scope (script will prompt if missing)

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

### Local k3d Cluster (build → import → restart)
```bash
# Build all three images
docker build -t ghcr.io/thatcatxedo/fastapi-platform-backend:dev backend/
docker build -t ghcr.io/thatcatxedo/fastapi-platform-frontend:dev frontend/
docker build -t ghcr.io/thatcatxedo/fastapi-platform-runner:dev runner/

# Import into k3d and restart
k3d image import ghcr.io/thatcatxedo/fastapi-platform-{backend,frontend,runner}:dev -c fastapi-platform-dev
kubectl rollout restart deployment/backend deployment/frontend -n fastapi-platform
```

Key details: Use `:dev` tag (not `:latest`) so k8s doesn't try to pull from GHCR.
Deployments use `imagePullPolicy: Never`. See `docs/LOCAL_DEV_CLUSTER.md` for full
dev workflow, common issues, and troubleshooting.

## Architecture

### Components
- **backend/**: FastAPI API that handles auth, app CRUD, and dynamically creates K8s resources
- **frontend/**: React + Monaco Editor for code editing, deployed via nginx
- **runner/**: Pre-built container that executes user code from ConfigMap
- **cli/**: `fp` CLI tool for local development and deployment (Python, Typer + Rich + httpx)

### Key Backend Structure
```
backend/
├── main.py              # FastAPI app setup, lifespan events
├── routers/             # API route handlers
│   ├── apps.py          # App CRUD, deploy, validate
│   ├── auth.py          # Login, signup, user management
│   ├── templates.py     # Template CRUD (global + user)
│   ├── admin.py         # Admin endpoints
│   └── metrics.py       # App metrics/health endpoints
├── deployment/          # K8s resource creation
│   ├── apps.py          # App deployments (ConfigMap, Deployment, Service, Ingress)
│   ├── viewer.py        # MongoDB viewer deployments
│   └── helpers.py       # Shared utilities
├── background/          # Background tasks
│   ├── cleanup.py       # Inactive app cleanup
│   └── health_checks.py # App health polling
├── templates/           # Template system
│   ├── loader.py        # YAML template loading with Pydantic validation
│   └── global/          # 8 built-in templates as individual YAML files
├── migrations/          # Startup migrations
└── seed_templates.py    # Loads templates from YAML files on startup
```

### Deployment Flow
When user deploys code:
1. Backend validates code (AST parsing, import whitelist, security checks)
2. Creates ConfigMap with user code (single file or multiple files)
3. Creates Deployment using runner image (mounts ConfigMap at `/code`)
4. Creates Service (port 80 → 8000)
5. Creates Traefik IngressRoute with subdomain routing
6. App accessible at `https://app-{app_id}.{APP_DOMAIN}` (e.g., `app-abc123.gatorlunch.com`)

### Runner Execution
`runner/entrypoint.py`:
1. Reads code from `CODE_PATH` env var (default `/code/main.py`)
2. Adds `/code` to `sys.path` for multi-file imports
3. Executes code in isolated namespace
4. Extracts `app = FastAPI()` or `app = FastHTML()` instance
5. Wraps with `/health` endpoint for K8s probes
6. Patches Swagger UI for relative OpenAPI paths
7. Starts uvicorn server

### CLI (`fp`)

The `fp` CLI lets developers work locally and deploy to the platform from the terminal.
Lives in `cli/`, installable as a Python package.

```bash
cd cli
uv venv && uv pip install -e .  # or: pip install -e .

# Authenticate
fp auth login https://platform.gatorlunch.com

# Scaffold + deploy
mkdir my-api && cd my-api
fp init                    # creates app.py + .fp.yaml
fp dev                     # local uvicorn with hot reload
fp deploy                  # deploy to platform

# Manage apps
fp list                    # table of all apps
fp status                  # app status (reads .fp.yaml)
fp logs                    # real-time log streaming
fp logs --no-follow        # fetch recent logs
fp pull <app-name>         # pull app code to local directory
fp push                    # save draft without deploying
fp validate                # offline code validation
fp open                    # open app URL in browser
fp delete <app-name>       # delete an app
```

**Key files:**
```
cli/
├── pyproject.toml              # Package config, entry point: fp = fp_cli.main:app
├── src/fp_cli/
│   ├── main.py                 # Typer app, registers all commands
│   ├── config.py               # ~/.fp/config.toml management
│   ├── project.py              # .fp.yaml read/write, file collection
│   ├── validation.py           # Vendored from backend/validation.py
│   ├── api/client.py           # httpx-based PlatformClient
│   └── commands/               # One file per command group
│       ├── auth.py             # auth login, whoami, logout
│       ├── init.py             # init (scaffold projects)
│       ├── deploy.py           # deploy (with Rich progress polling)
│       ├── apps.py             # list, status, open, delete
│       ├── logs.py             # logs (WebSocket + HTTP fallback)
│       ├── validate.py         # offline validation
│       ├── dev.py              # local dev server
│       ├── pull.py             # pull code from platform
│       └── push.py             # push draft to platform
```

**Config:** `~/.fp/config.toml` stores platform URL + JWT token per platform.
**Project:** `.fp.yaml` in project root with `name` and `entrypoint` fields.
**Validation:** `cli/src/fp_cli/validation.py` is vendored from `backend/validation.py`.
When updating backend validation rules, copy the file to keep them in sync.

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
- `BASE_DOMAIN` - Platform UI domain (default: `platform.gofastapi.xyz`)
- `APP_DOMAIN` - User app subdomain base (default: `gatorlunch.com`, apps at `app-{id}.{APP_DOMAIN}`)
- `INACTIVITY_THRESHOLD_HOURS` - App cleanup threshold (default: 24)

## CI/CD

GitHub Actions (`.github/workflows/build.yaml`) builds and pushes images on push to `main`:
- Images tagged `ts-{timestamp}-{short_sha}` for Flux compatibility
- Registry: `ghcr.io/thatcatxedo/fastapi-platform-{backend,frontend,runner}`
- Flux Image Automation in homelab-cluster picks up new tags and updates deployments

## Related Repositories

- **homelab-cluster/**: GitOps repo with Flux, contains K8s manifests for deploying this platform
- **fastapi-platform-cluster-foundation/**: Cluster baseline setup (k3d, Traefik, MongoDB, Cloudflared). Run `./setup.sh` to bootstrap a cluster, `./destroy.sh` to tear down.

## Kubectl Access

```bash
export KUBECONFIG=/Users/dbuck/.kube/configs/homelab-cluster-ruben/config
kubectl get pods -n fastapi-platform
kubectl logs -n fastapi-platform deployment/backend
```

## Code Validation Rules

User code is validated in `backend/routers/apps.py`:
- Must define an `app` instance (FastAPI or FastHTML)
- Allowed imports configurable by admin (defaults include: fastapi, pydantic, typing, datetime, json, math, random, uuid, re, collections, itertools, functools, enum, dataclasses, decimal, hashlib, base64, urllib.parse, html, http, pymongo, jinja2, os, fasthtml, python_multipart)
- Blocked patterns: `__import__`, `eval`, `exec`, `compile`, `open`, `socket`, `subprocess`, `os.system`, `os.popen`, `os.spawn`

### Multi-file Mode
- Max 10 files per app
- Max 100KB per file, 500KB total
- Entrypoint must be `app.py`
- All files validated for imports and blocked patterns

## Templates

Templates are stored as individual YAML files in `backend/templates/global/`:
- Loaded on startup via `seed_templates.py`
- Validated with Pydantic before insertion
- Support single-file (`code` field) and multi-file (`files` dict) formats
- Users can save their own templates via "Save as Template" in editor

### Direct MongoDB Template Management (for Claude Code)

Templates can be managed directly via MongoDB, bypassing the YAML → commit → CI → restart cycle. This enables instant template creation and modification.

**List templates:**
```bash
kubectl exec -n fastapi-platform deployment/backend -- python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
for t in db.templates.find({}, {'name':1,'mode':1,'framework':1,'is_global':1}).sort('name',1):
    scope = 'G' if t.get('is_global') else 'U'
    print(f'[{scope}] {t.get(\"mode\",\"single\"):5} {(t.get(\"framework\") or \"-\"):8} {t[\"name\"]}')
"
```

**Get template details:**
```bash
kubectl exec -n fastapi-platform deployment/backend -- python3 -c "
import json
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
t = db.templates.find_one({'name': 'TEMPLATE_NAME'})
t['_id'] = str(t['_id'])
print(json.dumps(t, indent=2, default=str))
"
```

**Update a file in a multi-file template:**
```bash
kubectl exec -n fastapi-platform deployment/backend -- python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
db.templates.update_one(
    {'name': 'TEMPLATE_NAME'},
    {'\$set': {'files.FILENAME.py': '''NEW_CODE_HERE'''}}
)
print('Updated')
"
```

**Create a new template:**
```bash
kubectl exec -n fastapi-platform deployment/backend -- python3 -c "
from pymongo import MongoClient
from datetime import datetime
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
db.templates.insert_one({
    'name': 'My Template',
    'description': 'Description here',
    'mode': 'multi',  # or 'single'
    'framework': 'fasthtml',  # or 'fastapi' or None
    'entrypoint': 'app.py',
    'files': {
        'app.py': '''from fasthtml.common import *
app, rt = fast_app()
@rt(\"/\")
def home(): return H1(\"Hello\")
''',
    },
    'is_global': True,
    'complexity': 'simple',
    'tags': ['example'],
    'created_at': datetime.utcnow()
})
print('Created')
"
```

**Template schema:**
- `name` (str): Unique template name
- `description` (str): Template description
- `mode` (str): "single" or "multi"
- `framework` (str|null): "fastapi", "fasthtml", or null
- `code` (str|null): Code for single-file templates
- `files` (dict|null): {filename: code} for multi-file templates
- `entrypoint` (str): Entry file for multi-file (default: "app.py")
- `is_global` (bool): True for system templates, False for user templates
- `complexity` (str): "simple", "medium", or "complex"
- `tags` (list): List of tag strings
- `created_at` (datetime): Creation timestamp
- `user_id` (str|null): Owner for user templates
