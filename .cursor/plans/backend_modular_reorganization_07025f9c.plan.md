---
name: Backend modular reorganization
overview: Reorganize the backend into domain-based modules (apps/, users/, viewer/, metrics/, admin/, templates/) with routes and services for each domain, plus core/ for infrastructure and shared/ for utilities.
todos:
  - id: structure
    content: Create directory structure with __init__.py files
    status: in_progress
  - id: core
    content: Move infrastructure to core/ (config, database, auth, lifespan)
    status: pending
  - id: shared
    content: Move utilities to shared/ (models, utils, validation)
    status: pending
  - id: deployment-split
    content: Split deployment.py into apps/k8s.py, viewer/k8s.py, core/mongo_uri.py
    status: pending
  - id: apps-domain
    content: Create apps/ domain (routes.py, service.py)
    status: pending
  - id: users-domain
    content: Create users/ domain (routes.py, service.py, mongo_users.py)
    status: pending
  - id: viewer-domain
    content: Create viewer/ domain (routes.py, service.py)
    status: pending
  - id: metrics-domain
    content: Create metrics/ domain (routes.py, service.py)
    status: pending
  - id: admin-domain
    content: Create admin/ domain (routes.py, service.py)
    status: pending
  - id: templates-domain
    content: Create templates/ domain (routes.py, seed_data.py)
    status: pending
  - id: background
    content: Move background tasks to background/
    status: pending
  - id: migrations
    content: Move migration scripts to migrations/
    status: pending
  - id: main-update
    content: Update main.py with new router imports
    status: pending
  - id: cleanup-old
    content: Delete old files and routers/ directory
    status: pending
  - id: verify
    content: Verify all files compile and no linter errors
    status: pending
isProject: false
---

# Backend Modular Reorganization

## Target Structure

```
backend/
├── main.py                    # Updated router registration
├── core/                      # Shared infrastructure
│   ├── __init__.py
│   ├── config.py              # From config.py
│   ├── database.py            # From database.py
│   ├── auth.py                # From auth.py
│   └── lifespan.py            # From lifespan.py
├── shared/                    # Shared utilities
│   ├── __init__.py
│   ├── models.py              # From models.py
│   ├── utils.py               # From utils.py
│   └── validation.py          # From validation.py
├── apps/                      # App domain
│   ├── __init__.py
│   ├── routes.py              # From routers/apps.py (thin)
│   ├── service.py             # Extracted business logic
│   └── k8s.py                 # K8s ops from deployment.py
├── users/                     # User domain
│   ├── __init__.py
│   ├── routes.py              # From routers/auth.py
│   ├── service.py             # User business logic
│   └── mongo_users.py         # From mongo_users.py
├── viewer/                    # MongoDB viewer domain
│   ├── __init__.py
│   ├── routes.py              # From routers/viewer.py
│   ├── service.py             # Viewer business logic
│   └── k8s.py                 # Viewer K8s ops from deployment.py
├── metrics/                   # Metrics domain
│   ├── __init__.py
│   ├── routes.py              # From routers/metrics.py
│   └── service.py             # Metrics aggregation
├── admin/                     # Admin domain
│   ├── __init__.py
│   ├── routes.py              # From routers/admin.py
│   └── service.py             # Admin business logic
├── templates/                 # Templates domain
│   ├── __init__.py
│   ├── routes.py              # From routers/templates.py
│   └── seed_data.py           # From seed_templates.py
├── background/                # Background tasks
│   ├── __init__.py
│   ├── cleanup.py             # From cleanup.py
│   └── health_checks.py       # From health_checks.py
└── migrations/                # One-off scripts
    ├── migrate_admin_role.py
    ├── migrate_mongo_users.py
    └── migrate_templates.py
```

## Migration Steps

### Phase 1: Create structure and move core/shared

- Create all directories with `__init__.py`
- Move: `config.py`, `database.py`, `auth.py`, `lifespan.py` -> `core/`
- Move: `models.py`, `utils.py`, `validation.py` -> `shared/`

### Phase 2: Split deployment.py (904 lines)

- Extract app K8s functions -> `apps/k8s.py`:
  - `create_configmap`, `create_deployment`, `create_service`, `create_ingress_route`
  - `create_app_deployment`, `update_app_deployment`, `delete_app_deployment`
  - `get_deployment_status`, `get_pod_logs`, `get_app_events`
  - Helper functions: `get_app_labels`, `create_or_update_resource`, etc.
- Extract viewer K8s functions -> `viewer/k8s.py`:
  - `create_mongo_viewer_deployment`, `create_mongo_viewer_service`, `create_mongo_viewer_ingress_route`
  - `create_mongo_viewer_resources`, `delete_mongo_viewer_resources`, `get_mongo_viewer_status`
  - Helper: `get_viewer_labels`, `get_viewer_name`
- Shared: `get_user_mongo_uri_secure`, `get_user_mongo_uri_legacy` -> `core/mongo_uri.py`

### Phase 3: Extract apps domain

- Create `apps/service.py` with business logic from `routers/apps.py`
- Create `apps/routes.py` with thin HTTP handlers
- Move helpers: `get_user_app`, `build_app_response`, `snapshot_version`, etc.

### Phase 4: Extract remaining domains

- `users/`: routes.py, service.py, mongo_users.py
- `viewer/`: routes.py, service.py, k8s.py
- `metrics/`: routes.py, service.py
- `admin/`: routes.py, service.py
- `templates/`: routes.py, seed_data.py

### Phase 5: Background and migrations

- Move `cleanup.py`, `health_checks.py` -> `background/`
- Move `migrate_*.py` -> `migrations/`

### Phase 6: Update main.py and imports

- Register routers from new locations
- Update all cross-module imports
- Delete old files and `routers/` directory

## Key Files Being Split


| Original                        | New Location(s)                                       |
| ------------------------------- | ----------------------------------------------------- |
| `deployment.py` (904 lines)     | `apps/k8s.py` + `viewer/k8s.py` + `core/mongo_uri.py` |
| `routers/apps.py` (611 lines)   | `apps/routes.py` + `apps/service.py`                  |
| `seed_templates.py` (789 lines) | `templates/seed_data.py`                              |
| `routers/admin.py` (185 lines)  | `admin/routes.py` + `admin/service.py`                |


## Verification

- All Python files compile with `python3 -m py_compile`
- No linter errors
- Import structure is clean and consistent

