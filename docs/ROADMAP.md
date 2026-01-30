# Roadmap

This roadmap organizes the long-term vision into shippable phases, starting with
developer/prototyper workflows and expanding toward full-stack builder experiences.

## North Star

The fastest path from idea to deployed full-stack app. Write code → deploy in
seconds → get a URL and a database. No git, no CLI, no Docker, no infrastructure.

## Differentiation

| Platform       | Gap we fill                                |
|----------------|--------------------------------------------|
| Replit         | Complex, expensive, not Python-API focused |
| Railway/Render | Requires git, no web editor                |
| PythonAnywhere | Dated UX, no instant deploy                |

Our niche: **Dead-simple FastAPI prototyping with batteries included.**

---

## Phase 0 — Foundations (complete)

- [x] Deploy UX with validate + deploy stages + error clarity
- [x] Deployment manifests in `deploy/` with overlays
- [x] Local dev cluster workflows documented
- [x] Logs + deployment events (basic lifecycle visibility)

## Phase 1a — Core Polish (complete)

**Goal:** Make the core loop feel fast and polished.

- [x] App Settings (env vars + secrets)
  - Per-app environment variables UI
  - Secure storage, injected at runtime
- [x] Error line highlighting in editor
- [x] OpenGraph meta tags on app URLs (better sharing)
- [x] App deletion (self-serve cleanup of throwaway apps)

## Phase 1b — Platform Database (complete)

**Goal:** Zero-config persistence for full-stack apps.

- [x] Per-user MongoDB database
  - One shared MongoDB instance, database per user (`user_{user_id}`)
  - Auto-provision on first use
  - Inject `PLATFORM_MONGO_URI` as magic env var
- [x] Add `pymongo` to runner image
- [x] Full-stack starter template ("Full-Stack Notes App" with MongoDB + HTML)
- [x] Allow `jinja2` import for server-rendered HTML

This enables:
```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
import os

app = FastAPI()
db = MongoClient(os.environ["PLATFORM_MONGO_URI"]).get_default_database()

@app.get("/", response_class=HTMLResponse)
def home():
    items = list(db.items.find({}, {"_id": 0}))
    return f"<html><body><h1>Items: {len(items)}</h1></body></html>"
```

Constraints (document, enforce later):
- 100MB storage per user
- No backup guarantees (homelab)
- Database-level isolation (not bulletproof)
- Resource limits per app (CPU/memory caps)
- Network isolation between apps (where feasible)
- Mongo query limits / timeouts for runaway ops
- Abuse guardrails (cryptomining or other misuse)

## Phase 1c — Database UI & Security (complete)

**Goal:** Give users visibility into their data and secure multi-tenancy.

- [x] Database stats page (`/database`)
  - Collection list with document counts
  - Total database size
  - Per-collection size and avg doc size
- [x] mongo-viewer integration
  - Subdomain routing (`mongo-{user_id}.{APP_DOMAIN}`)
  - Basic auth with rotate credentials
- [x] Per-user MongoDB authentication
  - Each user gets dedicated MongoDB credentials
  - Credentials created on signup
  - User apps can only access their own database
  - Prevents cross-user data access

## Phase 1d — Admin & Access Control (complete)

**Goal:** Secure the platform and enable administrative oversight.

- [x] Admin role
  - First user to sign up becomes admin automatically
  - `is_admin` flag in user document
  - Admin-only API endpoints with role check middleware (`require_admin`)
- [x] Signup control
  - Admin setting: allow public signups (on/off)
  - When off, only admin can create new users
  - Stored in platform settings collection
- [x] Admin dashboard (`/admin`)
  - User list with app counts, last activity
  - Platform stats: total users, apps, running apps, templates
  - Recent activity feed (signups, deploys)
- [x] User management
  - List users with app counts
  - Delete user (cascades to apps, MongoDB user, database)
  - Admin can create users manually when signups disabled
- [x] Multi-admin support
  - Admins can promote/demote other users to co-admin
  - `PATCH /api/admin/users/{user_id}/admin` endpoint
  - Safety checks: can't demote yourself, can't remove last admin
  - Role toggle button in admin dashboard user list

## Phase 1e — User Observability (complete)

**Goal:** Help users understand how their apps are performing.

- [x] App metrics (lightweight)
  - Request count (last 24h)
  - Error count (last 24h)
  - Avg response time
  - Display on Dashboard app cards
- [x] Recent errors panel
  - Last N errors with timestamps
  - Error type classification (client/server)
  - API endpoint: `GET /api/apps/{id}/errors`
- [x] Health status badge
  - Green/yellow/red based on recent health checks
  - Background job polls `/health` every 60s
  - API endpoint: `GET /api/apps/{id}/health-status`
- [x] Metrics API endpoints
  - `GET /api/apps/{id}/metrics` — aggregated metrics
  - `GET /api/apps/{id}/errors` — recent errors
  - `GET /api/apps/{id}/health-status` — health summary
- [x] TTL-indexed storage
  - Observability data auto-expires after 24 hours
  - Keeps database lean without manual cleanup

Implementation notes:
- Health checks use aiohttp to poll app `/health` endpoints
- Traefik log parsing disabled (requires cross-namespace RBAC)
- Metrics stored in MongoDB with TTL indexes

## Phase 1f — Drafts & Safety (complete)

**Goal:** Enable iteration without deployment risk.

- [x] Clone app
  - Duplicate with new ID from latest draft or deployed code
- [x] Draft save (explicit save without deploy)
  - `PUT /api/apps/{app_id}/draft` endpoint stores draft code
  - Ctrl+S keyboard shortcut in editor
  - "Save Draft" button in editor header
- [x] "Deployed vs Latest" indicator
  - Track `deployed_code` vs current code via hash comparison
  - UI shows "Up to date" / "Unsaved changes" / "Changes not deployed"
- [x] Version history (last 10 deploys)
  - `GET /api/apps/{app_id}/versions` returns history
  - `POST /api/apps/{app_id}/rollback/{index}` reverts to previous version
  - "History" button opens modal with preview and rollback
- [x] Deployment restart on code change
  - Fixed: ConfigMap updates now trigger pod restart
  - Added `platform.gofastapi.xyz/code-hash` annotation to pod template
  - When code changes, hash changes → K8s triggers rolling update
  - Previously: ConfigMap updated but pod kept running old code in memory

## Phase 1g — Codebase Quality (complete)

**Goal:** Improve maintainability and reduce large file sizes.

- [x] Backend reorganization
  - Split `deployment.py` (904 lines) into `deployment/` package:
    - `k8s_client.py` — K8s API client initialization
    - `helpers.py` — Shared utilities (MongoDB URI builders, K8s helpers)
    - `apps.py` — App deployment operations (ConfigMap, Deployment, Service, Ingress)
    - `viewer.py` — MongoDB viewer deployment operations
    - `__init__.py` — Re-exports for backwards compatibility
  - Grouped background tasks into `background/` package:
    - `cleanup.py` — Inactive app/viewer cleanup
    - `health_checks.py` — App health polling
  - Grouped migrations into `migrations/` package:
    - `admin_role.py` — First user admin migration
    - `mongo_users.py` — Per-user MongoDB auth migration
    - `templates.py` — Template seeding migration
- [x] Admin dashboard improvements
  - Added MongoDB stats (user DBs, storage, collections, documents)
  - Compact horizontal layout for stats
  - Two-column layout: users table + activity sidebar

Files unchanged (appropriately sized):
- `routers/apps.py` (611 lines) — Cohesive, helpers are route-specific
- `seed_templates.py` (789 lines) — Mostly template data/content
- All other modules — Under 250 lines each

---

## Quick Wins

Small improvements that can be shipped quickly between major phases:

- [ ] App descriptions/notes
  - Add optional `description` field to app documents (stored in MongoDB)
  - Display description on dashboard app cards
  - Editable in app settings or app page header
  - Helps users document what each app does, especially as app count grows
- [ ] Save applications as templates
  - Allow users to promote an app into the template library
  - Capture code, metadata, and version at save time

---

## Phase 2 — Multi-File Mode (in progress)

**Goal:** Support real-world app structure without losing simplicity.

**Status:** Implementation plan created. See `docs/architecture-reviews/` for detailed implementation plan.

- [ ] Project structure
  - Files: `app.py`, `routes.py`, `models.py`, `services.py`, `helpers.py` (FastAPI preset)
  - Files: `app.py`, `routes.py`, `models.py`, `services.py`, `components.py` (FastHTML preset)
  - Tabbed file editor with fixed file set per framework preset
- [ ] Build/run model
  - Multi-file ConfigMap with all files mounted at `/app`
  - Entrypoint via `CODE_PATH` env var (e.g., `/app/app.py`)
  - Runner adds `/app` to `sys.path` for imports
- [ ] Size limits for bundled projects (guardrail for ConfigMap/archives)
  - Max 10 files, 100KB per file, 500KB total
- [ ] Backward compatibility
  - Single-file mode remains default
  - New apps can choose single-file or multi-file mode
  - Framework selection: FastAPI (API-focused) or FastHTML (HTML/HTMX-focused)

## Phase 3 — Custom Dependencies

**Goal:** Unlock real-world apps that need extra packages.

- [ ] Curated allow-list extensions
- [ ] Per-app `requirements.txt` (validated against allow-list)
- [ ] Build-time install or dynamic runtime install
- [ ] UI for dependency management
- [ ] Hard constraints (no native extensions, no system packages)

## Phase 4 — Auth Templates

**Goal:** Help builders ship protected APIs fast.

- [ ] JWT auth starter template
  - Login + token issue + protected route
  - Add `python-jose` to runner image
- [ ] Platform auth helper module (optional)

## Phase 5 — LLM Assistant

**Goal:** Use AI to accelerate scaffolding and iteration.

- [ ] Inline assistant panel
- [ ] Scaffolding prompts ("Generate CRUD", "Add auth")
- [ ] Safety model: suggest → preview → confirm → apply

## Phase 6 — Monetization & Limits

**Goal:** Provide sustainable tiers without surprising users.

- [ ] Free tier limits (apps, storage, requests)
- [ ] Pro tier (higher limits, custom domains)
- [ ] Team/shared apps (optional)

---

## Future / Needs Validation

These are ideas that need real user feedback before committing:

- **Container Image Automation** — Current gap: CI builds versioned tags
  (`ts-{timestamp}-{sha}`) but deployments only reference `:latest`, and no
  Flux Image Automation is configured to pick up new tags. Result: manual
  `kubectl rollout restart` required after every CI build. Options to explore:
  - Flux Image Automation with ImageRepository/ImagePolicy CRDs to auto-update
    manifests when new `ts-*` tags appear
  - GitHub Actions webhook to trigger rollout after image push
  - Add `kubectl rollout restart` step to CI workflow (simplest)
  - Use `imagePullPolicy: Always` with a rolling update annotation
- **Advanced Admin Observability** — Prometheus/Grafana stack, alerting,
  detailed resource tracking. Only if lightweight metrics prove insufficient.
- **GridFS Templates** — File upload/storage patterns. Wait for user demand.
- **FastHTML Templates** — HTML-first framework templates. Interesting but niche.
- **Custom Domains** — CNAME support. Enterprise feature, low priority.
- **Platform-Managed Auth** — Central user store + per-app access. Complex,
  defer until clear need.
- **Multi-Admin Support** — (Implemented in Phase 1d) Admins can now
  promote/demote users. Role hierarchy (viewer, editor, admin) could be
  added if more granular permissions are needed.

---

## Success Metrics

- **Time from idea → deployed app** (target: under 60 seconds)
- **Deploy success rate** (target: >95%)
- **Full-stack capability** — can users build HTML + database apps?
- **Repeat usage** — do builders come back?
- **Shareability** — are deployed URLs being shared?
- **Cleanup effectiveness** — inactive apps removed within 24 hours
