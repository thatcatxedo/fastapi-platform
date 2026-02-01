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
- [x] Allowed imports configuration
  - Admin-editable allowlist for code validation
  - Overrides default allowed imports globally
- [x] User management
  - List users with app counts
  - Delete user (cascades to apps, MongoDB user, database)
  - Admin can create users manually when signups disabled
- [x] Multi-admin support
  - Admins can promote/demote other users to co-admin
  - `PATCH /api/admin/users/{user_id}/admin` endpoint
  - Safety checks: can't demote yourself, can't remove last admin
  - Role toggle button in admin dashboard user list

## Phase 1e — User Observability (partial)

**Goal:** Help users understand how their apps are performing.

- [x] App metrics (lightweight) - **backend implemented, UI removed**
  - Request count (last 24h)
  - Error count (last 24h)
  - Avg response time
  - ~~Display on Dashboard app cards~~ (removed - Traefik RBAC not configured)
- [x] Recent errors panel
  - Last N errors with timestamps
  - Error type classification (client/server)
  - API endpoint: `GET /api/apps/{id}/errors`
- [x] Health status badge - **backend implemented, UI removed**
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
- Traefik log parsing requires cross-namespace RBAC (not configured)
- Dashboard metrics column removed until RBAC is set up
- Dashboard links simplified to icon buttons (↗ 📋 📄)

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
- [x] Save applications as templates
  - "Save as Template" button in editor
  - User templates stored separately from global templates
  - Full CRUD: create, edit, delete own templates
  - Templates modal with tabs: All / My Templates / Global

---

## Phase 2 — Multi-File Mode (complete)

**Goal:** Support real-world app structure without losing simplicity.

- [x] Project structure
  - Files: `app.py`, `routes.py`, `models.py`, `services.py`, `helpers.py` (FastAPI preset)
  - Files: `app.py`, `routes.py`, `models.py`, `services.py`, `components.py` (FastHTML preset)
  - Tabbed file editor with add/remove file support
- [x] Build/run model
  - Multi-file ConfigMap with all files mounted at `/code`
  - Entrypoint via `CODE_PATH` env var (e.g., `/code/app.py`)
  - Runner adds `/code` to `sys.path` for imports between files
- [x] Size limits for bundled projects
  - Max 10 files, 100KB per file, 500KB total
  - Validation enforced in backend
- [x] Backward compatibility
  - Single-file mode remains default
  - New apps can choose single-file or multi-file mode
  - Framework selection: FastAPI (API-focused) or FastHTML (HTML/HTMX-focused)
- [x] Template system refactor
  - Templates stored as individual YAML files (`backend/templates/global/`)
  - Template loader with Pydantic validation
  - Multi-file template support (files dict in YAML)

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

## Phase 5 — LLM Assistant (in progress)

**Goal:** Use AI to accelerate scaffolding and iteration.

**Architecture:** n8n as integration hub with tool-use for platform operations.

### Completed

- [x] n8n deployment in cluster
  - Self-hosted n8n alongside platform in `fastapi-platform` namespace
  - Kubernetes manifests: `deploy/base/n8n-*.yaml`
  - No PVC (ephemeral data) - workflows sync from git on startup
  - IngressRoute at `n8n.gatorlunch.com` (requires local cluster access)
- [x] Backend chat infrastructure
  - `backend/chat/` module with tools, service, models
  - `backend/routers/chat.py` - SSE streaming endpoints
  - `POST /api/chat/conversations` - Create conversation
  - `GET /api/chat/conversations` - List conversations
  - `POST /api/chat/conversations/{id}/messages` - Send message (SSE stream)
  - MongoDB collections: `conversations`, `messages`
- [x] Chat tools for Claude
  - `create_app` - Create and deploy apps (single-file and multi-file)
  - `update_app` - Update app code and redeploy
  - `get_app` - Get app details including code
  - `get_app_logs` - Fetch pod logs for debugging
  - `list_apps` - List user's apps
  - `delete_app` - Delete an app
  - `list_databases` - List user's MongoDB databases
- [x] n8n workflow management
  - `scripts/n8n-helper.sh` - CLI for workflow operations
  - Workflow JSON stored in `n8n-workflows/chat-workflow.json`
  - Auto-sync via helper script (uses n8n REST API)

### In Progress

- [x] n8n webhook workflow
  - Chat workflow calls Anthropic API with messages + tools
  - Returns structured response for backend to parse
  - Accessible at `http://n8n.localhost` (local only)
  - Env var access enabled via `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- [x] Frontend chat UI
  - Chat page with conversation sidebar (`/chat`, `/chat/:id`)
  - Message list with SSE streaming
  - Tool execution status display
  - Files: `frontend/src/pages/Chat/`, `frontend/src/hooks/useChat.js`

### TODO

- [ ] BYOK (Bring Your Own Key)
  - Users provide their own LLM API keys
  - Keys stored encrypted in user settings
  - Passed to n8n workflows at runtime
- [ ] Multi-provider support
  - Claude (Anthropic)
  - GPT-4 (OpenAI)
  - Other providers via n8n integrations
  - User selects preferred provider in settings
- [ ] Platform-aware prompts
  - System prompt includes all constraints (allowed imports, forbidden patterns)
  - MongoDB integration patterns
  - Single-file vs multi-file mode awareness
  - Template examples for context
- [ ] Safety model
  - Validate all AI-generated code before showing to user
  - Diff view for suggested changes
  - Accept/reject workflow
  - Rate limiting per user

### Known Issues

- ~~n8n uses emptyDir (no persistence)~~ **Fixed**: Now uses PVC for persistence
- n8n requires one-time UI setup after fresh deploy (create owner, generate API key)
  - Data persists across restarts with PVC
  - License auto-activates via `N8N_LICENSE_ACTIVATION_KEY` env var
- n8n accessible at `http://n8n.localhost` (requires `/etc/hosts` entry)

### Future Improvements

- **Move n8n to cluster-foundation** — n8n is infrastructure, not app-specific.
  Would allow sharing across multiple applications and simplify platform deploy.

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
- **Multiple Databases per User** — High priority. Currently each user gets one
  database (`user_{user_id}`) with multiple collections. Want to allow users to
  create multiple isolated databases for different projects. Would require:
  - UI for database management (create, delete, select active)
  - Per-app database selection in app settings
  - Updated `PLATFORM_MONGO_URI` injection per app
  - Storage quota tracking across all user databases

---

## Success Metrics

- **Time from idea → deployed app** (target: under 60 seconds)
- **Deploy success rate** (target: >95%)
- **Full-stack capability** — can users build HTML + database apps?
- **Repeat usage** — do builders come back?
- **Shareability** — are deployed URLs being shared?
- **Cleanup effectiveness** — inactive apps removed within 24 hours
