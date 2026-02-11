# Roadmap

This roadmap organizes the long-term vision into shippable phases. Completed phases
are preserved as historical record. Future phases reflect a strategic shift toward
stateful serverless for self-hosters, informed by competitive analysis and UX rethinking.

## North Star

Deploy Python APIs from your browser. Each app gets its own database. Scales to zero
when idle. Runs on your cluster.

The core metric is **time-to-first-request**: how fast can someone go from "I found
this platform" to "my code is running and I just called it." Target: under 3 minutes.

## Differentiation

| Platform           | Gap we fill                                          |
|--------------------|------------------------------------------------------|
| Replit             | Complex, expensive, not Python-API focused            |
| Railway/Render     | Requires git, no web editor, no included database     |
| PythonAnywhere     | Dated UX, no instant deploy                           |
| Coolify/CapRover   | No scale-to-zero, no browser editor, not serverless   |
| OpenFaaS           | Scale-to-zero paywalled, CLI-only, license concerns   |
| Knative            | Heavy (~1GB RAM control plane), requires Istio        |
| faasd              | Single-tenant, CLI-only, no web editor                |
| Val Town           | Cloud-only, JavaScript-focused, no self-hosting       |

Our niche: **Self-hosted Cloud Run with a built-in editor and database.**

No single feature here is unique. Railway has easy deploys. Val Town has a browser
editor. OpenFaaS has scale-to-zero. What's unique is the combination: browser editor
+ CLI + built-in database + scale-to-zero + self-hosted. Nobody packages all of these
together.

Three features carry the most weight:

1. **Browser editor with instant deploy** — the adoption hook. This is what makes
   someone try the platform. Write code, hit deploy, get a URL. Under 3 minutes from
   signup to first request. Nothing else in the self-hosted space offers this.
2. **CLI tool (`fp`)** — the retention hook. The browser editor gets people started,
   but developers with real workflows live in their local editor. `fp init`, `fp dev`,
   `fp deploy` makes the platform a daily-driver tool, not a novelty. Apps created in
   the browser can be pulled down and developed locally, and vice versa.
3. **Scale-to-zero** — the sustainability hook. A homelab cluster can't run 20
   always-on pods for apps that get hit twice a day. Sleep/wake makes multi-tenant
   feasible on small clusters and is what makes the platform genuinely serverless
   rather than just "a web editor that deploys containers."

### What we deliberately don't compete on

- Multi-language support (Python is the focus)
- Multi-cloud deployment
- GitHub-based CI/CD pipelines (that's Coolify territory)
- Enterprise IAM / SSO

### Infrastructure advantages (from cluster foundation)

The cluster foundation (`fastapi-platform-cluster-foundation`) provides infrastructure
that directly enables the zero-config story:

- **Wildcard Cloudflare tunnel** — `*.gatorlunch.com` routes through Cloudflare Edge to
  Traefik. Every deployed app gets public HTTPS automatically with zero DNS or TLS
  configuration. This is a huge part of why time-to-first-request can be under 3 minutes.
- **MongoDB with `readWriteAnyDatabase` + `userAdminAnyDatabase`** — The platform user
  can create per-user databases and MongoDB users on the fly. The "database just works"
  story has solid infrastructure backing.
- **No network policies (currently)** — All pods can reach all pods. Simplifies the
  scale-to-zero wakeup proxy. Network egress controls for user pods (see Tech Debt)
  should be added before any public launch.
- **Small cluster footprint** — k3d with 1 server + 1 agent. Resource efficiency matters,
  which strengthens the case for scale-to-zero over always-on pods.
- **No monitoring stack** — No Prometheus, Grafana, or Loki in the foundation. The "logs
  in the dashboard" feature (Phase 3) must pull from the K8s API directly (`kubectl logs`
  equivalent). This has implications for Phase 4: when a pod scales to zero, its logs
  disappear unless captured first. See Phase 4 notes on log persistence.

---

## Completed Phases

### Phase 0 — Foundations (complete)

- [x] Deploy UX with validate + deploy stages + error clarity
- [x] Deployment manifests in `deploy/` with overlays
- [x] Local dev cluster workflows documented
- [x] Logs + deployment events (basic lifecycle visibility)

### Phase 1a — Core Polish (complete)

**Goal:** Make the core loop feel fast and polished.

- [x] App Settings (env vars + secrets)
  - Per-app environment variables UI
  - Secure storage, injected at runtime
- [x] Error line highlighting in editor
- [x] OpenGraph meta tags on app URLs (better sharing)
- [x] App deletion (self-serve cleanup of throwaway apps)

### Phase 1b — Platform Database (complete)

**Goal:** Zero-config persistence for full-stack apps.

- [x] Per-user MongoDB database
  - One shared MongoDB instance, database per user (`user_{user_id}`)
  - Auto-provision on first use
  - Inject `PLATFORM_MONGO_URI` as magic env var
- [x] Add `pymongo` to runner image
- [x] Full-stack starter template ("Full-Stack Notes App" with MongoDB + HTML)
- [x] Allow `jinja2` import for server-rendered HTML

### Phase 1c — Database UI & Security (complete)

**Goal:** Give users visibility into their data and secure multi-tenancy.

- [x] Database stats page (`/database`)
- [x] mongo-viewer integration with subdomain routing
- [x] Per-user MongoDB authentication

### Phase 1d — Admin & Access Control (complete)

**Goal:** Secure the platform and enable administrative oversight.

- [x] Admin role (first user auto-promoted)
- [x] Signup control (on/off toggle)
- [x] Admin dashboard (`/admin`)
- [x] Allowed imports configuration
- [x] User management with cascade deletion
- [x] Multi-admin support

### Phase 1e — User Observability (partial)

**Goal:** Help users understand how their apps are performing.

- [x] App metrics API (backend implemented, UI removed pending Traefik RBAC)
- [x] Recent errors panel
- [x] Health status badge (backend implemented, UI removed)
- [x] Metrics API endpoints (`/metrics`, `/errors`, `/health-status`)
- [x] TTL-indexed storage (24h auto-expiry)

Note: Dashboard metrics UI was removed because Traefik RBAC for log parsing is not
configured. The backend APIs exist and will be resurfaced in Phase 3.

### Phase 1f — Drafts & Safety (complete)

**Goal:** Enable iteration without deployment risk.

- [x] Clone app
- [x] Draft save (explicit save without deploy)
- [x] "Deployed vs Latest" indicator
- [x] Version history (last 10 deploys) with rollback
- [x] Deployment restart on code change (code-hash annotation)

### Phase 1g — Codebase Quality (complete)

**Goal:** Improve maintainability and reduce large file sizes.

- [x] Backend reorganization (`deployment/`, `background/`, `migrations/` packages)
- [x] Admin dashboard improvements (MongoDB stats, compact layout)

### Phase 2 — Multi-File Mode (complete)

**Goal:** Support real-world app structure without losing simplicity.

- [x] Project structure (FastAPI and FastHTML presets)
- [x] Multi-file ConfigMap with entrypoint via `CODE_PATH`
- [x] Size limits (50 files, 100KB/file, 500KB total)
- [x] Template system refactor (individual YAML files, Pydantic validation)

### LLM Assistant (in progress, cross-cutting)

**Goal:** AI-assisted code authoring and debugging.

Completed:
- [x] Backend chat infrastructure (`backend/chat/`, SSE streaming)
- [x] Chat tools: `create_app`, `update_app`, `get_app`, `get_app_logs`,
  `list_apps`, `delete_app`, `list_databases`
- [x] Agent tools: `list_templates`, `get_template_code`, `validate_code_only`,
  `test_endpoint`, `diagnose_app`
- [x] Agentic loop (multi-step tool use, 10-iteration safety limit)
- [x] Platform-aware system prompts
- [x] Frontend chat sidebar in editor

Remaining:
- [ ] BYOK (users provide their own API keys)
- [ ] AI-generated code validation before showing to user
- [ ] Diff view for suggested changes with accept/reject

The chat sidebar will be carried forward into the new frontend (Phase 3). It stays
in the editor as a tool, not a standalone page.

---

## Future Phases

### Phase 3 — Frontend Overhaul

**Goal:** Rebuild the frontend around three screens optimized for the
write-deploy-operate loop. Replace the current multi-page layout with a focused
experience that makes the platform feel like a different product.

#### Design foundation

- [ ] Adopt Tailwind CSS + component library (Shadcn/ui or similar)
  - Replace all custom CSS and CSS variables
  - Consistent design tokens, spacing, typography
  - Dark mode support (editor is already dark; unify the whole app)
- [ ] Replace `useAppState` god hook (~750 lines, 40+ state variables)
  - Extract into focused stores with Zustand: `useEditorStore`, `useDeployStore`,
    `useAppStore`
  - Clean separation: code editing state vs deployment state vs app metadata
- [ ] Break monolithic page components into composable pieces
  - Current: Dashboard (300+ lines), Database (400+), Admin (480+), Editor (480+)
  - Target: No component file over 200 lines

#### Screen 1: Editor (rethought)

- [x] Code on the left, **test panel on the right**
  - Backend proxy endpoint `POST /api/apps/{app_id}/proxy` (solves CORS)
  - Method picker, path input, headers/body editors, response viewer
  - Status code, response body, latency — with request history
  - Test and Chat share the sidebar slot via header toggle buttons
- [x] Single deploy button (validates automatically, shows inline errors on failure)
  - Removed separate "Validate" button and deploy confirmation modal
  - Backend validates during deploy; errors highlight the error line in Monaco
  - Ctrl+Enter keyboard shortcut deploys directly
- [x] Static assets + dynamic file management
  - Start every new app as a single file — no mode/framework choice upfront
  - Framework auto-detected from code (AST app creation pattern)
  - Non-`.py` files (CSS, JS, SVG, HTML, JSON, TXT) allowed with size-only validation
  - Runner auto-mounts `static/` directory via Starlette `StaticFiles`
  - File list sidebar replacing hardcoded tabs (flat list, 180px sidebar)
  - "+" dropdown to add files (7 templates), inline rename/delete buttons
  - Entrypoint (`app.py`) protected from rename/delete
- [x] Database shown as a binding indicator, not a separate panel
  - Compact "DB: name" badge inline in the app name row
  - Click badge to expand settings drawer; orange warning when code uses MongoDB
  - Database selector available for both new and existing apps (was new-only)
- [x] Env vars in a collapsible settings drawer
  - Single "Settings" drawer combines database selector + env vars
  - Header shows summary even when collapsed (env var count, DB name)
  - Replaces standalone DatabaseSelector, EnvVarsPanel, and MongoDB warning banner
- [x] Deployment progress with real K8s event streaming
  - "Validating... Creating resources... Starting... Ready!" — not a spinner
- [ ] Chat sidebar carries forward from current implementation

#### Screen 2: App Dashboard (new)

- [ ] Status badge: running / sleeping / error — one word, color-coded
- [ ] URL with click-to-copy and click-to-open
- [ ] **Recent requests table**
  - Last N requests with timestamp, method, path, status code, latency
  - Click a failed request to see the traceback / error detail
  - This is the "Runs" concept from serverless, simplified for HTTP apps
- [ ] Tailing logs — right there, not behind a separate page or panel
- [ ] Database section — collection list, document counts, inline browse
  - Replaces the standalone Database page and separate viewer pod deployment
  - Embedded data inspector for simple read operations

#### Screen 3: Apps List (complete)

- [x] App rows: name, status badge, URL, last activity time, inline metrics
- [x] Search by name, filter by status (All/Running/Deploying/Error pills)
- [x] Clickable stats cards double as status filters
- [x] Aggregate 24h metrics inline with stats row
- [x] Contextual actions per status (Edit/Open/Docs/Logs/Errors for running, Edit/Logs for error)
- [x] Replaces Dashboard page in-place — same route, same nav link

#### Template Management

- [x] Edit existing templates from the template gallery
  - EditTemplateModal for name, description, complexity, tags
  - Users edit own templates; admins edit global templates via separate endpoints
- [x] Hide/show templates
  - `is_hidden` field with hide/unhide endpoints
  - Visibility toggle in TemplatesModal and Admin dashboard
  - Hidden templates shown at reduced opacity in admin view
- [x] Admin template management
  - Templates table in admin dashboard (all global + user templates)
  - Toggle visibility, delete, edit from admin UI
  - Uses `/api/admin/templates/` endpoints

#### In-App MongoDB Explorer

Simple database browser built into the platform UI, replacing the need to launch a
separate mongo-express viewer pod for basic data inspection.

- [ ] Databases & collections view
  - List all databases the current user has access to (their `user_{id}` database)
  - Show collections within each database with document counts and storage size
  - Admins see all databases across the platform
- [ ] Collection browser
  - Paginated document list with JSON viewer
  - Sort by `_id` or indexed fields
  - Basic filter (JSON query input, like `{"status": "active"}`)
- [ ] Read-only by default
  - No insert/update/delete from the explorer (that's what the app code is for)
  - Reduces risk of accidental data mutation
  - Optional: admin-only write mode behind a toggle (future)
- [ ] Replaces mongo-viewer pod deployment
  - Current flow: deploy a full mongo-express instance per user as a separate pod
  - New flow: built-in explorer served by the platform backend, no extra pods
  - Significant resource savings (one less deployment per user who wants data visibility)

Backend:
- `GET /api/databases` — list user's databases with collection stats
- `GET /api/databases/{db_name}/collections` — list collections with counts
- `GET /api/databases/{db_name}/{collection}/documents` — paginated document list
- Admin variants for cross-user browsing

This is separate from the per-app "database section" in Screen 2, which shows
collections relevant to a specific app. The explorer is a standalone page for
browsing all your data.

#### What gets removed or folded in

- **Dashboard page** → replaced by Apps List (Screen 3) + per-app dashboard (Screen 2)
- **Database page** → database browsing moves into App Dashboard (Screen 2)
- **WelcomeScreen mode selection** → removed; apps start as single file, grow naturally
- **Separate Validate button** → deploy validates automatically
- **Admin page** → kept but accessible via settings icon, not primary navigation

#### Backend work for Phase 3

- [x] Request logging middleware
  - Pure ASGI middleware in runner captures method, path, status code, latency per request
  - Background thread batches writes to `_platform_request_logs` in user's MongoDB database
  - TTL index (7 days), compound index on `(app_id, timestamp)`
  - Endpoint: `GET /api/apps/{app_id}/requests` (paginated)
- [x] WebSocket endpoint for log streaming
  - `WS /api/apps/{app_id}/logs/stream` — real-time log tailing via K8s pod log follow
  - Token-based auth via query parameter, automatic pod reconnection
  - Frontend LogsPanel tries WebSocket first, falls back to polling
- [x] Remove mode/framework requirement from app creation
  - Auto-detect framework from AST (FastAPI vs FastHTML app creation pattern)
  - Mode inferred from request shape (files present → multi, else single)
  - WelcomeScreen simplified to single "Start from scratch" card
- [x] Embed database stats in app detail response
  - Include collection list and document counts in `GET /api/apps/{app_id}`
  - No separate viewer deployment needed for basic data browsing

### Phase 4 — Scale-to-Zero

**Goal:** Apps sleep when idle and wake on first request. No wasted cluster resources.

Scale-to-zero is what makes the platform sustainable on small clusters and genuinely
serverless. Without it, every deployed app is an always-on pod consuming resources
whether it gets traffic or not. It also removes the current 24h inactivity deletion —
apps stay deployed but scale to zero replicas instead.

- [ ] Wakeup proxy
  - Lightweight service (or Traefik middleware) that intercepts requests to sleeping apps
  - On request to a scaled-to-zero app: buffer request, scale Deployment to 1 replica,
    wait for readiness probe, forward buffered request
  - Timeout budget: 2-5 seconds for cold start (pod scheduling + image pull + uvicorn)
  - Runner image must be pre-pulled on nodes to minimize cold start
- [ ] Sleep lifecycle
  - After N minutes of no traffic (configurable, default 15 min), scale to 0 replicas
  - Preserve ConfigMap, Service, IngressRoute — only Deployment replicas change
  - New app status: `sleeping` (distinct from `running`, `error`, `deleted`)
  - Replaces the current 24h inactivity deletion for running apps
- [ ] Cold start UX
  - Loading page shown while app wakes (not a raw 504)
  - "Cold start" marker visible in request history
  - Frontend shows "sleeping" status with explanation
- [ ] Pre-pull runner image on cluster nodes
  - DaemonSet or node-level pull policy to ensure fast cold starts
  - Without this, first wake after image update can take 30+ seconds
  - Foundation cluster is k3d with 2 nodes — pre-pull is cheap but critical
- [ ] Log persistence across sleep cycles
  - When a pod scales to zero, its stdout/stderr logs are gone (no Loki/Fluentd in
    the cluster foundation)
  - Options: (a) flush logs to MongoDB before sleep, (b) the request logging middleware
    from Phase 3 captures per-request data independently of pod logs, (c) add lightweight
    log collector later
  - At minimum, the Phase 3 request logging (stored in MongoDB with 7-day TTL) ensures
    request-level observability survives pod restarts and scale-to-zero cycles
  - Full stdout log persistence is a Phase 4+ concern — the request table is enough
    for most debugging

### Phase 5 — CLI Tool (`fp`)

**Goal:** Make the platform accessible to developers who work locally. The browser
editor gets people started; the CLI is what makes them stay.

The browser editor is great for first impressions, quick edits, and templates. But
developers with real workflows edit code in VS Code, Neovim, or their IDE of choice.
If the only way to use the platform is through the browser, you lose every developer
who has an established local workflow. The CLI is the adoption multiplier — it turns
the platform from a toy into a tool.

**The core flow:**

```bash
pip install fp-cli

# Register with a platform deployment (one-time)
fp auth https://platform.gatorlunch.com
# Opens browser for login, stores token + platform URL
# "Authenticated as dude on platform.gatorlunch.com"

# Scaffold a new project
mkdir my-api && cd my-api
fp init
# Creates app.py with hello world starter + .fp.yaml config

# Develop locally with hot reload
fp dev
# Runs at localhost:8000 using the actual runner image
# PLATFORM_MONGO_URI injected automatically

# Deploy with one command
fp deploy
# Validates → uploads → deploys → prints URL
# "Deployed to https://app-abc123.gatorlunch.com"
```

No Docker knowledge. No Kubernetes. No YAML beyond two lines. No git hooks.

| Moment                          | Best tool      |
|---------------------------------|----------------|
| First time trying the platform  | Browser editor |
| Quick template-based project    | Browser editor |
| Hotfix to a running app         | Browser editor |
| Building a real multi-file project | CLI + local editor |
| CI/CD pipeline deploy           | CLI            |
| Teaching/demos                  | Browser editor |

The platform API is the same for both. An app created in the browser can be pulled
down with `fp pull` and developed locally. An app deployed via CLI can be edited in
the browser. No lock-in to either workflow.

#### Implementation

Built in Python (Typer + Rich + httpx). Lives in `cli/` directory, installable via
`pip install fp-cli` or `uv tool install fp-cli`. Validation logic vendored from
`backend/validation.py` for offline checks with zero drift.

#### Authentication and platform registration

- [x] `fp auth login <platform-url>` — register the CLI with a platform deployment
  - Stores platform URL + token + username in `~/.fp/config.toml`
  - Interactive: prompts for username/password
  - Headless: `fp auth login <url> --token <token>` for CI environments
- [x] Multiple platform support
  - `fp auth` stores multiple platform registrations in config.toml
  - `--name` flag to manage named platform configs
  - Per-project override via `platform` field in `.fp.yaml`
- [x] `fp auth whoami` — show current user, email, platform, admin status
- [x] `fp auth logout` — remove stored credentials

#### Scaffolding and project structure

- [x] `fp init` — scaffold a new project in the current directory
  - Interactive framework choice (FastAPI or FastHTML)
  - Creates `app.py` with working hello world + `.fp.yaml` config
  - `fp init --template <name>` — scaffold from a platform template
  - App name derived from directory name (overridable with `--name`)
- [x] Project manifest (`.fp.yaml`)
  ```yaml
  name: my-api
  entrypoint: app.py
  ```
  Two required fields. Optional fields:
  ```yaml
  platform: platform.gatorlunch.com  # override default platform
  env:
    SOME_API_KEY: "${SOME_API_KEY}"   # pulled from local env
  database: true                       # opt into MongoDB binding
  ```

#### Local development

- [x] `fp dev` — run the app locally with uvicorn + hot reload
  - Reads `.fp.yaml` for entrypoint and env vars
  - Injects `PLATFORM_MONGO_URI=mongodb://localhost:27017` if `database: true`
  - `--port` flag (default 8000)
- [ ] `fp dev --docker` — run inside the actual platform runner image
  - Same Python version, same packages, same entrypoint behavior as prod
  - Not yet implemented; current mode uses local Python
- [ ] `fp dev --remote-db` — use actual platform MongoDB with user credentials

#### Deploy and operate

- [x] `fp deploy` — one command deploy
  - Reads `.fp.yaml` for app name and entrypoint
  - Collects all files (`.py`, `.css`, `.js`, `.svg`, `.html`, `.json`, `.txt`)
  - Auto-detects mode (single vs multi) from file count
  - If app exists (same name): updates. If new: creates.
  - Polls deploy status with Rich spinner, prints URL on success
  - Resolves env vars from `.fp.yaml` (`${VAR}` syntax from local env)
- [x] `fp logs` — tail logs from deployed app
  - Default: real-time streaming via WebSocket
  - `--no-follow`: fetch recent logs and exit
  - `--since 1h` / `--since 30m` / `--since 5s`: time-scoped
  - Falls back to HTTP if WebSocket fails
- [x] `fp list` — Rich table of all apps (name, status, URL, last deploy)
- [x] `fp status [app-name]` — detailed single-app status (reads `.fp.yaml` if no name)
- [x] `fp open [app-name]` — open app URL in browser
- [x] `fp delete <app-name>` — delete with confirmation (`--yes` to skip)

#### Bridging browser and local workflows

- [x] `fp pull <app-name>` — pull existing app code to local directory
  - Creates `.fp.yaml` + all app files locally
  - Prefers deployed code over draft code
  - Works for apps created in the browser — start there, continue locally
- [x] `fp push` — push local edits back to platform without deploying
  - Updates the saved code on the platform (like "Save Draft" in the browser)
  - `fp deploy` to actually deploy the changes

#### Validation and safety

- [x] `fp validate` — run platform validation checks locally
  - AST parsing for syntax errors
  - Import whitelist checking
  - Blocked pattern scanning
  - Entrypoint verification (app instance required)
  - Validation logic vendored from `backend/validation.py` — same rules offline
  - Rich-formatted output with file names and line numbers on errors

#### Distribution

- [x] `pip install fp-cli` / `uv tool install fp-cli`
  - Python package with Typer, httpx, websockets, PyYAML, watchfiles
  - Entry point: `fp` command via `[project.scripts]`
  - Requires Python >= 3.10

#### Remaining (Phase 5b)

- [ ] Browser-based OAuth flow (instead of username/password prompt)
- [ ] `fp dev --docker` — run inside runner image for full parity
- [ ] `fp dev --remote-db` — use platform MongoDB credentials locally
- [ ] `.fpignore` file support (gitignore-style file exclusion)
- [ ] `fp env` — manage environment variables from CLI
- [ ] `fp db` — browse databases from CLI
- [ ] `fp export [app-name]` — download app as a ZIP file
  - Exports all app files (code, static assets) + `.fp.yaml` manifest
  - If no name given, uses current project's `.fp.yaml`
  - Useful for backups, sharing apps, or migrating between platform instances
  - Backend endpoint: `GET /api/apps/{app_id}/export` returns ZIP
- [ ] Shell completion installation command
- [ ] Pre-deploy local validation (run `fp validate` automatically before upload)

### Phase 6 — Async Invocation & Triggers

**Goal:** Move beyond request/response HTTP into event-driven workflows. This is where
the platform becomes genuinely useful for automation, webhooks, and background jobs.

#### Async invocation

- [ ] `POST /api/invoke/{app_id}` — queue-backed async invocation
  - Immediate `202 Accepted` response with `run_id`
  - Payload forwarded to app when it processes the job
  - Run states: `queued` -> `running` -> `succeeded` -> `failed` -> `retried`
- [ ] Run history in App Dashboard
  - Each invocation tracked: trigger, payload, status, duration, result/error
  - Click a failed run to see traceback + one-click replay
  - Filterable by status, time range
- [ ] Retry policy
  - Configurable per-app (default: 3 retries with exponential backoff)
  - Manual replay button for any failed run
- [ ] Job queue implementation
  - MongoDB-backed queue (avoids adding Redis as a dependency)
  - Worker process polls queue, wakes app if sleeping, forwards request
  - Concurrency limit per app (default: 1)

#### Triggers

Start with two trigger types beyond HTTP:

- [ ] Cron trigger
  - Cron expression stored in app document
  - Backend scheduler makes HTTP call to app on schedule
  - Shows next/last run time in App Dashboard
- [ ] Webhook trigger
  - Stable webhook URL per app: `POST /api/webhook/{app_id}/{path}`
  - Wakes app if sleeping, forwards payload
  - Useful for GitHub webhooks, Stripe events, etc.

#### What we deliberately defer

- Complex event buses (Kafka, NATS, RabbitMQ connectors)
- `handler(event, context)` function interface — keep full FastAPI apps
- Backend adapter abstraction over OpenFaaS/Knative — complexity trap

### Phase 7 — Custom Dependencies

**Goal:** Unlock real-world apps that need packages beyond the runner's built-in set.

- [ ] Per-app `requirements.txt` (validated against admin allow-list)
- [ ] Runtime install at pod startup (pip install from requirements before running code)
  - Adds cold start time but avoids per-app image builds
  - Cached via PVC or init container with shared pip cache
- [ ] UI for dependency management in editor settings drawer
- [ ] Hard constraints: no native extensions, no system packages
- [ ] Admin-configurable package allow-list (extends current import allow-list)

### Phase 8 — Monetization & Limits

**Goal:** Sustainable tiers without surprising users.

- [ ] Usage metering (requests, compute time, storage per user)
- [ ] Free tier limits (apps, storage, requests, databases)
- [ ] Pro tier (higher limits, custom domains, longer sleep threshold)
- [ ] Team/shared apps (optional, needs validation)

---

## Technical Debt / DX Improvements

Infrastructure-level improvements that can be shipped alongside or between phases.

### High Priority

- ~~Static assets support for FastHTML apps~~ — moved into Phase 3b (coupled with file management)

- [ ] **Network egress controls (NetworkPolicy)**
  - Default deny egress for user app pods
  - Allow: DNS, MongoDB service (internal), admin-allowlisted external domains
  - More urgent than pod securityContext given credential exposure

- [ ] **Pod security hardening**
  - Add `securityContext`: non-root, read-only root fs, drop all capabilities
  - Add `emptyDir` at `/tmp` if runner needs writes

### Medium Priority

- [ ] **Replace exec() with importlib in runner**
  - Better stack traces, cleaner module boundaries, no global injection
  - Also support `create_app()` factory pattern for forward compatibility

- [ ] **Circular import detection in validation**
  - Build import graph from AST, warn on cycles
  - Low effort, high value for multi-file debugging

- [ ] **Dry-load validation (subprocess + timeout)**
  - Attempt to import entrypoint in subprocess with 1-2s timeout
  - Catches import-time crashes before K8s deploy

- [x] **Raise file limit from 10 to 50**
  - ConfigMap 1MB limit is the real constraint, not file count
  - Adjust 500KB total size limit if needed

### Low Priority / Nice-to-Have

- [ ] **Show available packages in editor UI**
- [ ] **HTMX-aware logging** (HX-* headers in log viewer)
- [ ] **Container Image Automation** (Flux ImagePolicy or CI webhook for rollouts)
- [ ] **App export/import** (download as ZIP via `fp export` or browser, upload to recreate)

---

## Future / Needs Validation

Ideas that need real user feedback or strategic clarity before committing:

- **Custom Domains** — CNAME support per app. Enterprise feature, low priority.
- **Platform-Managed Auth** — Central user store + per-app access. Complex, defer.
- **GitHub "Clone from repo" in templates** — Import starter code without full CI/CD.
  Avoids Coolify territory while letting users bootstrap from existing code.
- **MongoDB change streams as trigger** — Deploy logic when documents change.
  Interesting differentiator but niche. Wait for demand.
- **Branch-based preview URLs** — Deploy from git branch to preview subdomain.
  Only relevant after CLI ships.
- **Multi-language support** — JavaScript/TypeScript runtime. Major scope expansion.
  Only if Python-only proves too limiting for adoption.

---

## Roadmap Sanity Check

Notes on phase ordering, scope risks, and dependencies.

### Phase ordering is sound

Phase 3 (Frontend) → 4 (Scale-to-Zero) → 5 (CLI) → 6 (Async) → 7 (Dependencies) → 8
(Monetization) follows a logical progression. Phase 5a (CLI MVP) was pulled forward
and shipped alongside Phase 3 since the CLI is backend-only and doesn't depend on the
frontend overhaul. The frontend overhaul gives you the
dashboard where scale-to-zero status is visible. Scale-to-zero is the core serverless
differentiator. CLI opens a second entry point. Async/triggers add depth for power users.
Dependencies unlock real-world use cases. Monetization comes last because it needs a
product worth paying for first.

### Phase 3 scope risk

Phase 3 is the largest phase by far: Tailwind migration, Zustand state rewrite, three new
screens, request logging middleware, WebSocket log streaming, auto-detection refactor,
embedded database browsing, and template management. This could easily become a
multi-month rewrite that blocks everything behind it.

**Mitigation:** Consider splitting Phase 3 into incremental deliverables:

- **3a — Backend APIs first.** ~~Request logging middleware, WebSocket log endpoint,~~ embedded
  DB stats. Request logging and WebSocket streaming are done. These are independently
  useful and unblock Phase 4 work in parallel.
- **3b — Editor improvements.** ~~Single deploy button~~, ~~inline test panel~~, ~~static assets +
  file list view~~, ~~database badge~~, ~~env vars drawer~~, ~~template management UI~~. **3b complete.**
- **3c — Design system + restructure.** Tailwind migration, Zustand stores, component
  decomposition. This is the "rewrite" part — do it last when the new screens are proven.

The `useAppState` refactor (750 lines, 40+ state variables) is important but can be done
incrementally. Extract one store at a time rather than rewriting everything at once.

### Phase 4 can start before Phase 3 finishes

The wakeup proxy and sleep lifecycle are backend-only. They don't depend on the new
frontend. The Phase 3 app dashboard with "sleeping" status badge is the UI for Phase 4,
but the backend can ship first with a simpler status indicator in the existing UI.

### Phase 7 cold start compounding

Custom dependencies (pip install at startup) compounds with scale-to-zero cold starts.
A sleeping app that needs to pip install packages before starting could have 10-30 second
wake times. The shared pip cache (PVC) is essential, not optional. Consider making the
cache a hard requirement for Phase 7, not an optimization.

### MongoDB as the only infrastructure dependency is a strength

The roadmap avoids introducing Redis (async queue uses MongoDB), avoids Knative/KEDA,
avoids external log collectors. Keeping MongoDB as the single stateful dependency is
a deliberate and good choice for a homelab platform. The foundation already deploys
MongoDB — no additional infra needed.

---

## Success Metrics

### Primary (the numbers that matter)

- **Time-to-first-request** — from signup to "my code responded to an HTTP call"
  (target: under 3 minutes)
- **Deploy success rate** (target: >95%)
- **Weekly active deployers** — users who deploy at least once per week

### Secondary

- **Cold start p95** — time from first request to sleeping app responding
  (target: under 5 seconds, Phase 4)
- **Repeat deployment frequency** — how often users redeploy (signals iteration)
- **Async adoption rate** — percent of apps using async invocation (Phase 6)
- **CLI vs browser ratio** — healthy split indicates both entry points working (Phase 5)
- **Database binding rate** — percent of apps using MongoDB (stickiness indicator)

---

## Reference Documents

- `docs/serverless-pivot-exploration.md` — Competitive landscape analysis, scale-to-zero
  architecture, CLI story, UX philosophy
- `docs/FUNCTION_MODE_DEEP_DIVE.md` — Async invocation model, runs/replay UX,
  trigger model, Mongo-as-binding concept
- `../fastapi-platform-cluster-foundation/` — Cluster bootstrap repo. Deploys Traefik,
  MongoDB, Cloudflare tunnel, Flux. Defines the infrastructure contract the platform
  builds on.
