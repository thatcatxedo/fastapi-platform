# Roadmap

This roadmap organizes the long-term vision into shippable phases, starting with
developer/prototyper workflows and expanding toward broader builder experiences.

## North Star

Make FastAPI prototyping feel instant, safe, and productive: edit → validate →
deploy → iterate, with clear feedback, multi-file projects, and optional AI
assistance.

## Phase 0 — Foundations (now)

- Solidify deploy UX (validate + deploy stages + error clarity).
- Deployment manifests in `deploy/` with overlays.
- Local dev cluster workflows documented.

## Phase 1 — Drafts & App Lifecycle (near-term)

**Goal:** enable iteration without deployment and show deploy freshness.

- Draft save (no deploy)
  - Explicit “Save Draft” action.
  - Backend stores draft code + timestamp.
  - Dashboard and Editor show “Saved vs Deployed” status.
- Deployed vs Latest
  - Track last deployed code hash and draft hash.
  - UI indicator: “Up to date” vs “Not deployed”.
- Clone App
  - Duplicate app with new ID and code from latest draft or last deployed.
  - Optional “clone with templates only” path for clean-start.

## Phase 2 — Multi-File Mode (core builder workflow)

**Goal:** support real-world app structure without losing simplicity.

- Project structure
  - Files like `main.py`, `routers/`, `services/`, `models/`, `schemas/`.
  - Simple file tree in editor with add/rename/delete.
- Build/run model
  - Bundle files into a runtime container mount or archive.
  - Entrypoint rule: `main.py` with `app = FastAPI()`.
- Backward compatibility
  - Single-file mode remains.
  - “Convert to multi-file” auto-scaffolds structure.

## Phase 3 — Metrics & Observability (basic app health)

**Goal:** give builders confidence their app is working.

- Metrics (MVP)
  - Requests per minute (RPM).
  - Error rate (4xx/5xx).
  - Last request timestamp.
- UX placement
  - Dashboard summary per app.
  - App detail pane with chart (last 1h, 24h).
- Implementation options
  - Minimal: Ingress/Traefik metrics + app labels.
  - Later: OpenTelemetry / Prometheus scraping.

## Phase 4 — Batteries-Included Auth (opt-in)

**Goal:** help builders ship protected APIs fast.

- Template: JWT auth app
  - Login + token issue + protected route.
  - Requires allowing `jose` import and dependency in runner image.
- Platform helper
  - Lightweight auth helper module or starter files.
- Future: platform-managed auth service
  - Central user store + per-app access rules.

## Phase 5 — LLM Assistant (builder accelerator)

**Goal:** use AI to speed up planning, scaffolding, and iteration.

- Inline assistant panel for code + file changes.
- Scaffolding prompts:
  - “Generate CRUD with auth”
  - “Add router + schema + tests”
- Safety model:
  - Suggest, preview, and apply with explicit confirmation.
- FastHTML influence (backend-first UI patterns)
  - Optional template set for HTML-first workflows and server-rendered UI.
  - Reference: FastHTML docs for idiomatic patterns and constraints.
    - https://www.fastht.ml/docs/llms-ctx.txt

## Notes on FastHTML (why it matters)

FastHTML is an HTML-first framework that favors server-rendered UI and fast
iteration. It’s a useful inspiration for “builder-first” workflows and could be
a future template category alongside REST APIs. Reference docs:
- https://www.fastht.ml/docs/llms-ctx.txt

## Metrics for Success

- Time from idea → deployed app (target: minutes).
- Deploy success rate and time-to-ready.
- Repeat usage (returning builders).
- NPS or quick “Was this useful?” feedback in editor.

