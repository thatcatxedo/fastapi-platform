# Serverless Pivot Exploration

*Discussion captured 2026-02-10*

Brainstorming session exploring what it would look like to transform fastapi-platform from a code-editing PaaS into a serverless platform, and whether there's a unique product identity in that space.

---

## Current Platform Summary

fastapi-platform is a multi-tenant platform where users write FastAPI/FastHTML code in a browser-based Monaco editor and deploy it as isolated Kubernetes pods. Key existing capabilities:

- **Browser-based editor** with multi-file support, drafts, version history, and rollback
- **Per-user MongoDB provisioning** - automatic credential creation (Fernet-encrypted), scoped database per user, `PLATFORM_MONGO_URI` injected into pods
- **MongoDB viewer** (mongo-express) deployed on-demand per user, auto-deleted after 48h inactivity
- **Code validation** - AST parsing, import whitelisting, blocked patterns (no subprocess, eval, exec, etc.)
- **Template system** - 12 built-in templates (YAML-defined), user-created templates
- **Multi-file projects** - up to 10 files, entrypoint-based, cross-file imports supported
- **Automatic HTTPS** via Traefik IngressRoutes
- **Inactivity cleanup** - background task deletes pods after 24h of no activity
- **AI chat sidebar** for code assistance
- **Runner architecture** - pre-built container image, code mounted via ConfigMap, exec'd in isolated namespace

## The Serverless Landscape (as of early 2025)

### Self-Hosted FaaS - Current State

| Platform | Status | Notes |
|----------|--------|-------|
| Knative Serving | Thriving (CNCF) | Gold standard, but heavy (~1GB RAM for control plane). Powers Cloud Run. |
| KEDA | Thriving (CNCF Graduated) | Scaling primitive, not a full platform. 60+ scalers including HTTP. |
| OpenFaaS CE | Active but constrained | Scale-to-zero paywalled. License backlash from community. ~25k GitHub stars. |
| faasd | Active | OpenFaaS without K8s. Beloved by homelabbers but CLI-only, same license concerns. |
| Fermyon Spin | Growing | Wasm-based, sub-ms cold starts. Python support still experimental. |
| Kubeless | Dead | Archived 2023. |
| Fn Project | Effectively dead | Oracle pivoted to managed OCI Functions. |
| Fission | Mostly dead | Innovative env pooling concept but development stalled. |
| OpenWhisk | Barely alive | IBM pivoted to Code Engine (Knative-based). |

### What Homelabbers Actually Use

Most homelabbers don't use "serverless" at all - they run Docker Compose containers. Those who want FaaS gravitate toward faasd, n8n/Node-RED for automation, or KEDA + plain Deployments on k3s. Coolify (self-hosted Heroku-like PaaS) has been gaining massive traction.

### The Market Gap

There's a clear gap for something that is:
- Simpler than Knative (no Istio, no complex CRDs)
- More open than OpenFaaS (no license restrictions on scale-to-zero)
- More capable than faasd (multi-tenant, web editor, not just CLI)
- More serverless than Coolify/CapRover (scale-to-zero, function-oriented)
- Has a browser-based editor (most FaaS platforms are CLI-only)

### Industry Trend: "Thick Serverless"

The industry is moving away from tiny functions toward **full applications with serverless properties** (scale-to-zero, managed deployment, no ops). Google Cloud Run is the poster child. This trend validates the current fastapi-platform approach of deploying full FastAPI apps rather than forcing a function handler interface.

## Proposed Direction: "Stateful Serverless for Self-Hosters"

### The Core Insight

Every FaaS platform handles state terribly. Lambda users jump through hoops with DynamoDB. OpenFaaS users are on their own. Meanwhile fastapi-platform already gives users a provisioned database per app with credentials injected automatically and a web viewer to inspect data.

### The Pitch

> Write a Python API in your browser. It gets a database automatically. It scales to zero when idle. It wakes on first request. Runs on your cluster.

### Target Audience

- **Homelabbers** who want to deploy small APIs (webhook handlers, home automation endpoints, personal tools) without wasting cluster resources 24/7
- **Small teams** who want internal tools with persistent data without provisioning infrastructure
- **Learners** who want to build real CRUD apps without DevOps

### One-Liner

> Deploy Python APIs from your browser. Each app gets its own database. Scales to zero when idle. Runs on your cluster.

## Key Features to Build (Priority Order)

### 1. Scale-to-Zero (Biggest Gap)

No need for Knative or KEDA. Custom lightweight approach using existing infrastructure:

- Backend already knows about every app and makes K8s API calls
- Health check polling and activity tracking already exist
- Traefik IngressRoutes already in place

**Approach:** A lightweight "wakeup" proxy. When a request hits an app scaled to zero, buffer the request, call K8s API to scale Deployment to 1, wait for readiness, forward request. After N minutes of no traffic, scale back to 0. The existing cleanup loop already does the "scale down" half.

Could be implemented as a Traefik middleware or small sidecar service. No heavy dependencies needed.

### 2. Cron/Scheduled Triggers

Second most requested trigger type after HTTP. Simple scheduler in backend that makes HTTP calls to deployed apps on a schedule. Store cron expressions in the app document in MongoDB.

### 3. Webhook/Event Invocation

Endpoint like `POST /api/invoke/{app_id}` that wakes the app if needed and forwards the payload. Turns every deployed app into a callable webhook endpoint.

### 4. Deeper MongoDB Integration

- Collection explorer embedded in editor sidebar (beyond the standalone viewer)
- Collection/document counts in app dashboard
- MongoDB change streams as trigger type (deploy when document inserted)

## What NOT to Do

- **Don't force a function handler interface.** Keep letting users write full FastAPI/FastHTML apps. The "container-as-function" model (Cloud Run style) is where the industry is heading.
- **Don't over-invest in Wasm.** Fermyon Spin has sub-ms cold starts, but Python Wasm support is experimental. Container cold starts of 2-5 seconds are acceptable with good UX (loading states, not 504s).
- **Don't try to be multi-cloud.** Strength is the integrated experience. A homelab platform that does one thing well beats a generic platform that does everything.

## GitHub Integration Analysis

### Three Possible Implementations

**Path A: "Deploy from repo"** - Users connect a repo, platform pulls code and deploys. This is what Coolify, Railway, Render do. Puts platform directly against Coolify (bad fight to pick - Coolify supports dozens of languages, has huge traction).

**Path B: "Editor to repo sync"** - Users write in browser editor, platform syncs to GitHub as backup/version control. Editor stays primary. Preserves the "write in browser, deploy instantly" identity.

**Path C: "Bidirectional"** - Import from repo to bootstrap, continue editing in browser. Or start in editor and export when project grows.

### The Validation Problem

Full GitHub integration creates a tension with the security model:

- Current model: import whitelisting, AST parsing, controlled package set in runner image
- Real repos need `requirements.txt`, arbitrary dependencies, potentially 50+ files
- Options:
  1. **Keep sandbox** - repos must conform to platform rules (limits what people can deploy)
  2. **Build per-app images** - parse requirements.txt, build Docker images per deploy (fundamentally different architecture, deploys go from seconds to minutes)
  3. **Hybrid** - browser editor keeps sandbox, GitHub path gets different pipeline

### Recommendation

Removing the file limit (10 -> 50+) is a no-brainer - costs nothing.

Full GitHub integration risks pulling toward Coolify territory. Better alternatives:
- **Simple CLI deploy** (`fp deploy .`) - tar up local files, POST to API, deploy via same ConfigMap path. Works for any VCS or no VCS.
- **"Clone from GitHub" in templates** - import starter code without full CI/CD pipeline
- **"Export to GitHub" button** - for users who want code in a repo for safety

The things that make the platform unique (zero-to-deployed in browser, database included, self-hostable) aren't strengthened by GitHub integration. Better to invest in scale-to-zero, CLI deploy, and richer MongoDB integration.

## What Makes Serverless Platforms Sticky

### Tier 1: Make-or-Break
1. **Developer experience** - speed from idea to running code (#1 differentiator)
2. **Cold start performance** - users intolerant of >2-3s cold starts
3. **Reliability** - function must work every time

### Tier 2: Strong Differentiators
4. Language/runtime support (Python + JS are table stakes)
5. Monitoring/observability (built-in logs >> "go check Grafana")
6. Automatic HTTPS and domains (already have this via Traefik)
7. Integrations/event sources (HTTP baseline, cron #2, then queues/webhooks)

### Tier 3: Nice-to-Have
8. Secrets management
9. Custom domains
10. Team/collaboration features
11. Version history/rollback (already have this)
12. Templates/marketplace (already have this)

### The Stickiness Trap
Most sticky platforms are ones where users build up **state and integrations** that are hard to migrate. The MongoDB integration is a strong stickiness factor - users who build data-driven apps won't easily move elsewhere.

## Competitive Positioning

- **Not competing with:** Lambda, Cloudflare Workers (cloud-hosted, massive scale)
- **Closest comparisons:** Val Town, Replit Deployments (browser code -> running service) but for self-hosted/homelab
- **Unique niche:** A self-hosted Cloud Run with a built-in editor and database - nobody else fills this spot

## Existing Assets That Translate Well

| Current Feature | Serverless Angle |
|----------------|-----------------|
| Inactivity cleanup (24h) | Becomes scale-to-zero with shorter threshold |
| MongoDB viewer (on-demand deploy, 48h TTL) | Prototype of scale-to-zero pattern |
| Health check polling | Basis for auto-scaling logic |
| Per-user MongoDB credentials | "Database included" differentiator |
| Code validation/sandboxing | Safety for shared clusters |
| Template system | Marketplace/quickstart for functions |
| Version history | Deployment rollback |
| Env vars support | Secrets management foundation |

## Cross-Reference: Function Mode Deep Dive Analysis

A separate document (`docs/FUNCTION_MODE_DEEP_DIVE.md`) explores what "Function Mode" could look like as a UX-focused addition to the platform. The following is an analysis of how that document's proposals relate to and complement the strategic direction outlined above.

### Where the Function Mode Doc Adds Value

**The `handler(event, context)` question.** The doc proposes supporting both a `handler(event, context)` contract and a FastAPI-compatible wrapper. This is the core design tension to resolve early. The strategic direction in this document favors "don't force a function handler interface, keep letting users write full FastAPI apps." The Function Mode doc hedges by supporting both, which could work but risks confusing the identity. Is it a function platform or an app platform? Trying to be both from day one might dilute both experiences. Worth resolving before building.

**Async invocation model is genuinely interesting.** The doc describes async invoke with `run_id`, queued execution, run states (`queued` -> `running` -> `succeeded` -> `failed`), retry, and replay. This is a real differentiator we hadn't explored above. Most self-hosted FaaS platforms have weak async stories (OpenFaaS's NATS-based async is frequently criticized). Nailing async invoke + run history + replay in the UI would be a feature businesses actually pay for.

**The "Runs" concept is the killer UX insight.** The proposed tab structure with `Invoke`, `Runs`, and `Logs` as separate views reframes the product from "here's your deployed app" to "here's a history of every time your code was called." That's a fundamentally different mental model and the right one for serverless. The current UI is oriented around editing and deploying. The Runs model orients around *operating*.

**Mongo-as-binding framing is stronger than "lean into MongoDB."** The doc goes beyond just emphasizing MongoDB as a differentiator - it frames the database as a declarative binding rather than just an injected env var. "Select database from dropdown, platform injects secure URI, scaffold helper appears in editor." That's cleaner than what exists now and makes the database feel like a first-class platform feature rather than plumbing.

### Where to Push Back

**The contract card is too many knobs for MVP.** The proposed settings surface (timeout, payload limits, memory, concurrency, retry policy, log retention) is a lot of configuration for a first release. Homelabbers don't want to configure concurrency limits. Ship with sensible defaults, expose settings later.

**The backend adapter strategy should be dropped.** Phase 3 mentions "optional backend adapter strategy (OpenFaaS/Knative) if needed." Abstracting over multiple backends is an enormous complexity trap and means building adapters for platforms you're trying to differentiate from. The custom lightweight approach (wakeup proxy + K8s API scaling) described in this document is simpler and more aligned with the self-hosted identity.

**Scale-to-zero mechanism is handwaved.** The Function Mode doc mentions "cold start happened marker" and "warm/cold/paused" status but doesn't describe the actual implementation. That's the hardest technical problem. The custom proxy approach described in this document (buffer request -> scale Deployment to 1 -> wait for readiness -> forward) fills that gap.

### How the Two Documents Complement Each Other

| Topic | This Document (Pivot Exploration) | Function Mode Deep Dive |
|-------|-----------------------------------|------------------------|
| Competitive positioning | Strong (landscape analysis, market gap) | Light |
| Scale-to-zero architecture | Concrete approach (proxy + K8s API) | Acknowledges need, no mechanism |
| GitHub integration tradeoffs | Detailed analysis with recommendation | Not addressed |
| UX and information architecture | Light | Strong (tab structure, invoke panel, runs) |
| Async invocation | Not explored | Detailed model with run states and replay |
| MongoDB framing | "Lean into it as differentiator" | "Binding concept" with UI scaffold |
| Personas and success metrics | Brief target audience sketch | Detailed personas, JTBD, and metrics |

**Recommended synthesis:** Take the async/runs/replay model and the Mongo-as-binding concept from the Function Mode doc. Combine with the lightweight custom scale-to-zero approach, competitive positioning, and "don't force a handler interface" stance from this document. That gives you a clear product identity with a concrete technical path.

## UX Philosophy: Simplicity Over Features

### The Core Friction This Platform Solves

A developer has Python code. They want it running at a URL. They don't want to think about Kubernetes, Docker, Traefik, ConfigMaps, Ingress, or any of it. The platform's job is to make that gap disappear.

Every concept, configuration step, or decision point added to the path between "I have code" and "it's live at a URL" is friction that loses users. The platforms that win developer adoption aren't the ones with the most features - they're the ones where the first experience feels like magic.

### The Function Mode Doc Overcomplicates Things

The Function Mode deep dive introduces triggers, invocation modes (sync/async/both), runtime presets, contract cards, run states, and trigger management tabs. That's the enterprise brain talking. A developer who wants to deploy a Python script doesn't want to think about "invocation mode" or "retry policy." They want:

1. Write code
2. It's running at a URL
3. I can see if it's broken

Everything else is either a sensible default or a setting they discover later when they need it.

### Where Current UX Has Friction

The existing flow is decent but has speedbumps:

**The mode choice upfront.** "Single file or multi file?" is a question the user shouldn't have to answer before they've started. Just give them an editor. If they need a second file later, let them add one. Start simple, grow as needed.

**Validate then deploy as two steps.** From the user's perspective, "deploy" should validate automatically. If validation fails, show the errors. If it passes, deploy. One button.

**The deploy wait with no feedback.** Pod scheduling takes seconds. During that time the user needs a status stream: "validating... creating resources... starting... ready!" Not a spinner with no context.

**Post-deploy is where most platforms fall apart.** The app is running. Now what? Where are the logs? Is it healthy? What happens when someone hits it and gets a 500? This is where a simplified version of the "Runs" concept has value - not as a complex invocation system, but as a simple "here's what happened when people called your code" view.

### The UX That Would Actually Win

Three screens:

**Screen 1: Editor.** Code on the left, a live test panel on the right. The test panel lets you send a request to your app and see the response inline - no need to open a new tab, copy the URL, use curl. Pick a path, choose GET/POST, add a body, hit send, see result. Like Postman built into the editor. Deploy is one button. Errors show inline with squiggly underlines. No separate validate step.

**Screen 2: App Dashboard.** After deploy, the app's home screen shows:
- **Status** (running / sleeping / error) - one word, color-coded
- **URL** - click to copy, click to open
- **Recent requests** - last 20 hits with status code, latency, timestamp. Click a failed request, see the traceback. This alone is a massive differentiator.
- **Logs** - tailing, filterable, right there (not in Grafana, not in kubectl)
- **Database** - collection list, document counts, click to browse. Not a separate viewer deployment - embedded in the dashboard.

**Screen 3: Apps List.** All your apps. Each card: name, status (running/sleeping), URL, last request time. That's it.

### What's Notably Absent From This UX

- No "trigger type" selection. Every app gets an HTTP endpoint. That's the trigger. Cron can come later as a setting, not a fundamental mode choice.
- No "sync vs async" decision. Everything is sync by default.
- No runtime configuration upfront. Defaults work. Settings exist but are tucked away.
- No "function vs app" mode split. It's all just "apps." Some are one file, some are ten. The platform doesn't care.

### The MongoDB UX Principle

The database shouldn't feel like a feature you opt into. It should feel like it's just there. When you create an app, you already have a database. The connection string is already in your environment. The first template people see should be a CRUD example that reads and writes data. The document browser lives in the app dashboard, not behind a separate deployment.

### The Real Competitive Moat Is Time-to-First-Request

If someone can go from "I found this platform" to "my code is running and I just called it" in under 3 minutes, you win. Vercel won because `git push` = deployed. Cloudflare Workers won because `wrangler deploy` = live globally. This platform's equivalent: paste code, click deploy, it's live with a database.

Everything else - scale-to-zero, cron triggers, async, teams, secrets - gets layered on after the core loop feels effortless.

## Local Development to Deploy: The CLI Story

### Why This Matters

The browser editor is great for quick edits, starting from templates, and first-time users. But developers with real workflows edit code in VS Code, Neovim, or their IDE of choice. If the only way to use the platform is through the browser editor, you lose every developer who has an established local workflow.

The answer isn't GitHub integration (which pulls toward Coolify territory). It's a CLI tool.

### The Ideal Flow

```bash
# One-time setup
pip install fp-cli
fp login https://platform.gatorlunch.com

# Start a new project
mkdir my-api && cd my-api
fp init
# Creates app.py with a hello world starter and .fp.yaml config

# Develop locally
fp dev
# Runs app at localhost:8000 with hot reload
# Injects PLATFORM_MONGO_URI pointing at a local or dev MongoDB

# Deploy
fp deploy
# Validates → uploads → deploys → returns URL
# "Deployed to https://app-abc123.gatorlunch.com"

# Monitor
fp logs         # Stream logs from deployed app
fp status       # Running / sleeping / error
fp open         # Opens app URL in browser
```

That's the whole flow. No Docker knowledge needed. No Kubernetes. No YAML. No git hooks.

### The Config File

Minimal `.fp.yaml` in the project root:

```yaml
name: my-api
entrypoint: app.py
```

That's it for the common case. Optional fields for when you need them:

```yaml
name: my-api
entrypoint: app.py
env:
  SOME_API_KEY: "${SOME_API_KEY}"  # pulled from local env
database: true                      # opt into MongoDB binding
```

No Dockerfile. No docker-compose.yaml. No kubernetes manifests. One file, two required fields.

### `fp dev` - Local Development With Production Parity

This is the key command. Two modes:

**With Docker (recommended):** Runs the actual platform runner image locally with your code mounted. Exact parity with production - same Python version, same pre-installed packages, same entrypoint behavior.

```bash
# What fp dev does under the hood:
docker run -v $(pwd):/code \
  -e PLATFORM_MONGO_URI=mongodb://localhost:27017/dev \
  -p 8000:8000 \
  ghcr.io/thatcatxedo/fastapi-platform-runner:latest
```

**Without Docker (fallback):** Runs with local Python + uvicorn. Less parity but zero setup friction. Warns the user that behavior may differ from production.

Both modes support hot reload on file changes.

### `fp deploy` - One Command Deploy

What happens when you run `fp deploy`:

1. Reads `.fp.yaml` for app name and entrypoint
2. Runs the same validation the platform does (AST parsing, import checking) - catches errors before upload
3. Tars up the project files (respecting a `.fpignore` file if present)
4. POSTs to the platform API (same endpoint the browser editor uses)
5. Platform creates/updates ConfigMap, Deployment, Service, IngressRoute
6. CLI polls for readiness, streams status
7. Prints the live URL

If the app already exists (same name, same user), it updates. If it's new, it creates. The user doesn't think about create vs. update.

### `fp logs` and `fp status` - Observability Without kubectl

```bash
fp logs                    # Tail logs from deployed app
fp logs --since 1h         # Last hour
fp status                  # One-line status: running, sleeping, error
fp status --detail         # Status + URL + last request + resource usage
```

These commands hit the platform's existing APIs. No kubectl, no kubeconfig, no namespace knowledge needed.

### What `fp dev` Solves for MongoDB

The biggest local dev challenge: the database. In production, `PLATFORM_MONGO_URI` is injected with per-user credentials. Locally, the developer needs a MongoDB instance.

Options `fp dev` could support:

1. **Local MongoDB** (default if detected): Points `PLATFORM_MONGO_URI` at `mongodb://localhost:27017/fp-dev-{app-name}`. Developer runs their own MongoDB via Docker or homebrew.
2. **Platform dev database** (with `fp dev --remote-db`): Uses the actual platform MongoDB with the user's real credentials. For when local data isn't sufficient or the developer wants to test against real data.
3. **Embedded** (stretch goal): `fp dev` starts a temporary MongoDB container automatically if Docker is available. Zero config.

### The CLI and Browser Editor Coexist

These aren't competing workflows. They serve different moments:

| Moment | Best tool |
|--------|-----------|
| First time trying the platform | Browser editor |
| Quick template-based project | Browser editor |
| Hotfix to a running app | Browser editor |
| Building a real multi-file project | CLI + local editor |
| CI/CD pipeline deploy | CLI |
| Teaching/demos | Browser editor |

The platform API is the same for both. An app created in the browser can be pulled down with `fp pull` and developed locally. An app deployed via CLI can be edited in the browser. No lock-in to either workflow.

### `fp pull` and `fp push` - Bridging the Two Worlds

```bash
# Pull an existing app from platform to local directory
fp pull my-api
# Creates .fp.yaml + all app files locally

# After local edits, deploy back
fp deploy
```

This replaces the need for GitHub integration for most workflows. The platform IS the remote. Users who want git can use git locally - the platform doesn't need to know or care about their VCS.

### What This Means for Packaging

The CLI should be:

- **Installable via pip** (`pip install fp-cli`) - meets Python developers where they are
- **Single binary option** - for users who don't want to pip install (Go or Rust binary, cross-compiled)
- **Minimal dependencies** - the CLI is a thin HTTP client. It doesn't need Kubernetes libraries, Docker SDKs, or anything heavy.

### Validation Locally

`fp validate` runs the same checks locally that the platform runs on deploy:

- AST parsing for syntax errors
- Import whitelist checking
- Blocked pattern scanning
- Entrypoint verification (does `app = FastAPI()` exist?)

This catches problems before the deploy round-trip. The same validation code from the backend could be packaged as a Python library that both the backend and CLI use.
