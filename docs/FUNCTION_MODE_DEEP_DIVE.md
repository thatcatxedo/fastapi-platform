# Function Mode Deep Dive

## Why This Exists

This document explores what "Function Mode" could look like for `fastapi-platform`, especially from the user perspective.

The goal is not to replace the current app model immediately. The goal is to add a clearer serverless flavor that can serve:

- homelabbers who want to deploy small callable APIs quickly, and
- businesses that currently evaluate OpenFaaS/Lambda style workflows.

---

## Core Product Idea

Function Mode should feel like:

- "Deploy a callable unit of Python logic"

rather than:

- "Deploy a long-running app service"

In practical UX terms, users should think in:

- trigger
- invoke
- run
- retry
- limits
- usage

instead of Kubernetes resources.

---

## Positioning

### Current North Star (already strong)

`fastapi-platform` already does:

- in-browser authoring
- code validation and deploy flow
- per-tenant isolation
- managed per-user/per-database Mongo credentials
- app URL provisioning

### Function Mode Positioning

**Stateful serverless for Python APIs.**

Not just "functions on Kubernetes." The wedge is:

- serverless invocation experience
- with built-in, tenant-scoped Mongo data access
- and browser-first developer experience

This is the differentiator versus infrastructure-first platforms.

---

## Personas and Jobs To Be Done

### Homelabber

Needs:

- instant deploy to URL
- minimal config
- low idle resource usage (scale-to-zero behavior)
- easy debugging and replay

Success criteria:

- first successful invoke in less than 5 minutes

### Business/Internal Platform User

Needs:

- predictable limits and runtime behavior
- reliability and retries
- auditability and observability
- secure tenant data access

Success criteria:

- can run webhooks/internal automations safely without learning cluster internals

---

## User Experience: End-to-End Journey

## 1) Create Function

Entry point: `New -> Function`.

User provides:

- function name
- runtime preset (`HTTP`, `Webhook`, `Cron`, optional `Async Worker`)
- invocation mode (`sync`, `async`, or both)
- optional data binding (`Mongo database`)

UI immediately shows:

- function invoke URL
- async URL (if enabled)
- timeout and memory defaults
- auth mode

## 2) Author Function

Editor opens with scaffold and contract.

Examples of supported contracts:

- `handler(event, context)` style
- lightweight FastAPI-compatible wrapper for existing patterns

Editor should include:

- inline validation feedback
- sample request payload
- expected response schema (or example)

## 3) Test Invoke (Before Deploy or Immediately After)

Built-in invoke panel:

- choose sync/async
- send JSON payload + headers
- view response, duration, status
- save test cases

For async:

- return `run_id`
- navigate to run timeline

## 4) Deploy + Operate

Post-deploy views focus on operations:

- invocations
- p95 latency
- error rate
- cold starts/warm status
- last successful run

Common actions:

- replay failed run
- rollback code version
- pause/resume function
- rotate token/secret

---

## Function Detail Page IA (Information Architecture)

Suggested tabs:

- `Code` - editor, drafts, deploy, rollback
- `Invoke` - manual invoke, request samples, curl snippets
- `Triggers` - HTTP, webhook, cron, async settings
- `Runs` - history with status and duration
- `Logs` - per-run logs and filters
- `Settings` - timeout, memory, concurrency, retries, auth, env vars
- `Data` - Mongo binding and access context
- `Usage` - invocation and compute metrics

This aligns interface with serverless user tasks.

---

## Invocation Model

### Sync Invocation

- request/response in one round trip
- good for APIs and lightweight transforms

UX details:

- status code
- response body
- latency
- explicit "cold start happened" marker when applicable

### Async Invocation

- immediate `accepted` response with `run_id`
- queued execution
- replay and retry support

Run states:

- `queued`
- `running`
- `succeeded`
- `failed`
- `retried`
- `cancelled` (later phase)

---

## Trigger Model (MVP-first)

Start with 3 trigger types:

- HTTP trigger
- Webhook trigger
- Cron trigger

Queue/event bus integrations can be phased in later.

---

## Mongo Integration as Product Moat

Function Mode should expose Mongo as a "binding" concept, not raw connection plumbing.

User flow:

- select database from dropdown
- platform injects secure scoped URI
- scaffold helper snippet appears in editor

Potential differentiators:

- per-function database selection
- clear visibility into which database each function uses
- correlation between runs and writes (request ID tagging)

This creates a "stateful serverless" category angle.

---

## Reliability and Safety UX

Each function should present a clear contract card:

- timeout
- payload limits (sync vs async)
- memory
- concurrency
- retry policy
- log retention

Each failed run should include:

- concise error summary
- stack trace
- likely cause classification
- one-click actions: replay, open code at error line

---

## Coexistence With Existing App Mode

App Mode should remain. Function Mode should be additive.

Suggested framing:

- `App Mode`: full API/web app deployment model
- `Function Mode`: callable, event-oriented, serverless workflow

Optional helper later:

- "Convert App to Function" for simple compatible apps

---

## Local-to-Cloud Developer Experience

Function Mode should not depend on the browser editor alone. Many developers will code locally in their own editor and only use the platform for deployment and operations.

The core promise should be:

- "Use your normal local workflow, then deploy to a live URL without touching Kubernetes."

### Ideal local workflow

1. initialize project metadata
2. run locally with platform-like behavior
3. run preflight checks
4. deploy from terminal
5. inspect logs/runs and iterate
6. rollback quickly if needed

### Suggested CLI command surface

- `fastapi-platform init`
- `fastapi-platform dev`
- `fastapi-platform validate`
- `fastapi-platform deploy`
- `fastapi-platform invoke`
- `fastapi-platform logs --follow`
- `fastapi-platform runs`
- `fastapi-platform env pull|push`
- `fastapi-platform rollback`

### Why this matters

- Removes friction for serious developers who prefer local IDEs.
- Prevents lock-in to web-only editing workflows.
- Makes onboarding easier for teams evaluating OpenFaaS/Lambda alternatives.
- Keeps infra complexity hidden while preserving power users' workflows.

---

## Features Needed for Easy Local-to-Platform Deploy

### 1) Project manifest

Add a lightweight manifest (for example: `platform.yaml`) containing:

- project kind (`app` or `function`)
- entrypoint
- trigger config
- runtime limits
- env var references

This gives deterministic deploy behavior and supports CI.

### 2) Local runtime parity

Provide a local dev command that mirrors platform runtime assumptions:

- same entrypoint behavior
- same validation constraints
- same environment variable conventions

This reduces "works locally, fails on platform" issues.

### 3) Preflight validation before upload

Before deployment, validate:

- syntax and security policy
- imports and blocked patterns
- file count and size limits
- entrypoint contract

Friendly errors should be shown locally before network upload.

### 4) Secrets and env sync

Developers need safe and simple env workflows:

- pull non-secret keys and metadata
- push updated values securely
- keep secrets out of git by default

### 5) Deploy diffs and faster redeploys

Show changed files and upload minimal deltas when possible.

Benefits:

- faster inner loop
- less bandwidth
- more confidence in what changed

### 6) CLI operations and debugging

Developers should be able to operate functions from terminal:

- invoke sync/async with payload
- inspect run statuses and durations
- tail logs
- replay failed runs

### 7) One-command recovery

Rollback must be simple and obvious in both UI and CLI.

Fast recovery is a trust multiplier for adoption.

---

## Local DX Prioritization

### Must-have for v1

- CLI auth + deploy + logs + invoke
- project manifest
- local parity runtime command
- preflight validation
- env/secrets sync basics
- rollback

### Nice-to-have for later

- branch-based preview URLs
- CI templates for auto deploy on merge
- editor extension integration
- cost/usage estimate at deploy time

---

## Technical Shape (High-Level)

Function Mode can be introduced without a full rewrite by adding a new execution type in the backend domain model.

Likely model extension:

- `kind: app | function`
- `invocation_mode: sync | async | both`
- `triggers: []`
- `runtime_limits: {timeout, memory, concurrency}`
- `function_status: warm/cold/paused` (or equivalent)

Existing strengths that can be reused:

- validation pipeline
- version history/drafts/rollback
- deployment orchestration abstraction (can be extended)
- metrics/health foundations
- secure Mongo credential generation

---

## MVP Scope Recommendation

Ship first:

- create/edit/deploy function
- sync invoke URL
- async invoke endpoint + run IDs
- run history + per-run logs
- basic retry for async failures
- timeout/memory/env vars/auth controls
- Mongo binding selection
- rollback/version history support

Defer initially:

- complex event buses and many source connectors
- advanced billing engine
- full multi-runtime dependency customization

---

## Rollout Plan

### Phase 1 - UX and Domain Layer

- Add Function Mode in UI and API models
- Keep runtime under existing deploy path where possible
- Introduce runs/invocation history in Mongo

### Phase 2 - Async and Triggers

- Add async queue-backed execution path
- Add cron/webhook trigger management
- Add retry/replay UX

### Phase 3 - Scale and Business Readiness

- strengthen quotas and rate limits
- richer observability
- clearer usage metering and plan enforcement
- optional backend adapter strategy (OpenFaaS/Knative) if needed

---

## Product Risks

- Cold start experience may hurt perceived performance if not messaged clearly.
- Architecture currently assumes always-on app deployments in places.
- Background jobs are currently in-process and should be decoupled for cleaner scaling.
- App deletion as inactivity policy should evolve to pause/scale semantics for function users.

---

## Success Metrics

Primary:

- time from create to first successful invoke
- function deploy success rate
- weekly active function creators
- replay-to-resolution time for failed runs

Secondary:

- async adoption rate
- percent of functions using Mongo binding
- repeat deployment frequency per user

---

## Summary

Function Mode is a strong strategic extension for `fastapi-platform`.

The strongest version is not "generic FaaS clone." The strongest version is:

- browser-first serverless Python
- with built-in tenant-safe Mongo data access
- and excellent invoke/debug/replay workflows

That can serve both homelab and business use cases while building on the architecture already in place.
