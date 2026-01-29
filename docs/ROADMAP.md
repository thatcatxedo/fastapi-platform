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

## Phase 1a — Core Polish (in progress)

**Goal:** Make the core loop feel fast and polished.

- [ ] App Settings (env vars + secrets)
  - Per-app environment variables UI
  - Secure storage, injected at runtime
  - *In progress*
- [ ] Error line highlighting in editor
- [ ] OpenGraph meta tags on app URLs (better sharing)
- [ ] App deletion (self-serve cleanup of throwaway apps)

## Phase 1b — Platform Database (near-term)

**Goal:** Zero-config persistence for full-stack apps.

- [ ] Per-user MongoDB database
  - One shared MongoDB instance, database per user (`user_{user_id}`)
  - Auto-provision on first use
  - Inject `PLATFORM_MONGO_URI` as magic env var
- [ ] Add `pymongo` to runner image
- [ ] Full-stack starter template (HTML + MongoDB CRUD)
- [ ] Allow `jinja2` import for server-rendered HTML

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

## Phase 1c — Drafts & Safety

**Goal:** Enable iteration without deployment risk.

- [ ] Draft save (explicit save without deploy)
  - Backend stores draft code + timestamp
  - "Saved vs Deployed" status indicator
- [ ] "Deployed vs Latest" indicator
  - Track deployed code hash vs draft hash
  - UI shows "Up to date" vs "Changes not deployed"
- [ ] Version history (last N deploys)
  - "Revert to last good deploy" action
- [ ] Clone app
  - Duplicate with new ID from latest draft or deployed code

## Phase 2 — Multi-File Mode

**Goal:** Support real-world app structure without losing simplicity.

- [ ] Project structure
  - Files: `main.py`, `routers/`, `models/`, `schemas/`
  - Simple file tree in editor with add/rename/delete
- [ ] Build/run model
  - Bundle files into ConfigMap or archive
  - Entrypoint: `main.py` with `app = FastAPI()`
- [ ] Size limits for bundled projects (guardrail for ConfigMap/archives)
- [ ] Backward compatibility
  - Single-file mode remains default
  - "Convert to multi-file" scaffolds structure

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

- **Metrics & Observability** — RPM, error rates, request history. May be
  overkill; logs + events might be enough.
- **GridFS Templates** — File upload/storage patterns. Wait for user demand.
- **FastHTML Templates** — HTML-first framework templates. Interesting but niche.
- **Custom Domains** — CNAME support. Enterprise feature, low priority.
- **Platform-Managed Auth** — Central user store + per-app access. Complex,
  defer until clear need.

---

## Success Metrics

- **Time from idea → deployed app** (target: under 60 seconds)
- **Deploy success rate** (target: >95%)
- **Full-stack capability** — can users build HTML + database apps?
- **Repeat usage** — do builders come back?
- **Shareability** — are deployed URLs being shared?
- **Cleanup effectiveness** — inactive apps removed within 24 hours
