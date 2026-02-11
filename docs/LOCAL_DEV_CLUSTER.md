# Local Dev Cluster (k3d / gatorlunch.com)

Notes on working with the local k3d development cluster for fastapi-platform.

## Cluster Setup

The cluster is created by `../fastapi-platform-cluster-foundation/setup.sh`. It runs
k3d with 1 server + 1 agent node, named `fastapi-platform-dev`.

```bash
# Bootstrap the cluster (Traefik, MongoDB, Cloudflare tunnel, etc.)
cd ../fastapi-platform-cluster-foundation
./setup.sh

# Deploy the platform
cd ../fastapi-platform
cp .env.example .env
./deploy.sh
```

Platform UI: `platform.gatorlunch.com`
User apps: `app-{id}.gatorlunch.com`

## Build and Deploy Workflow

The cluster uses locally-built Docker images with the `:dev` tag. This avoids
pulling from GHCR (where `:dev` doesn't exist) and gives fast iteration.

### Build all three images

```bash
# Run these in parallel for speed
docker build -t ghcr.io/thatcatxedo/fastapi-platform-backend:dev backend/
docker build -t ghcr.io/thatcatxedo/fastapi-platform-frontend:dev frontend/
docker build -t ghcr.io/thatcatxedo/fastapi-platform-runner:dev runner/
```

### Import into the k3d cluster

```bash
# Import all at once
k3d image import \
  ghcr.io/thatcatxedo/fastapi-platform-backend:dev \
  ghcr.io/thatcatxedo/fastapi-platform-frontend:dev \
  ghcr.io/thatcatxedo/fastapi-platform-runner:dev \
  -c fastapi-platform-dev
```

### Restart deployments to pick up new images

```bash
kubectl rollout restart deployment/backend deployment/frontend -n fastapi-platform
kubectl rollout status deployment/backend deployment/frontend -n fastapi-platform
```

### Update existing user app deployments

User app deployments don't automatically pick up new runner images. After importing
a new runner image, restart any running user apps:

```bash
# Find user app deployments
kubectl get deployments -n fastapi-platform -o name | grep '^deployment.apps/app-'

# Restart them
kubectl rollout restart deployment/app-XXXXX -n fastapi-platform
```

## Image Tag Strategy

**Why `:dev` instead of `:latest`?**

- `:latest` → Kubernetes defaults to `imagePullPolicy: Always` → tries to pull from
  GHCR on every pod restart → fails if GHCR doesn't have the image
- `:dev` → Kubernetes defaults to `imagePullPolicy: IfNotPresent` → uses the locally
  imported image without trying to pull

**`imagePullPolicy: Never`**

The deploy script patches deployments with `imagePullPolicy: Never` to guarantee
Kubernetes never tries to pull from GHCR. This is critical — without it, any pod
reschedule (node restart, eviction, etc.) will fail with `ImagePullBackOff`.

If you see `ImagePullBackOff` on a pod, check the image pull policy:

```bash
kubectl get deployment backend -n fastapi-platform \
  -o jsonpath='{.spec.template.spec.containers[0].imagePullPolicy}'
```

Fix it:

```bash
kubectl patch deployment backend -n fastapi-platform --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"Never"}]'
```

## RUNNER_IMAGE Environment Variable

The backend uses `RUNNER_IMAGE` to determine which image to deploy for user apps.
For local dev, this must point to the `:dev` tag:

```bash
# Check current value
kubectl exec -n fastapi-platform deployment/backend -- printenv RUNNER_IMAGE

# Set it (if not already configured by deploy.sh)
kubectl set env deployment/backend -n fastapi-platform \
  RUNNER_IMAGE=ghcr.io/thatcatxedo/fastapi-platform-runner:dev
```

## Common Issues

### ImagePullBackOff

**Cause:** Kubernetes trying to pull an image from GHCR that only exists locally.

**Fix:** Patch `imagePullPolicy` to `Never` (see above). Make sure the image was
imported with `k3d image import`.

### Wrong container name in kubectl commands

Backend deployment container is named `backend`, not `runner`. Check with:

```bash
kubectl get deployment backend -n fastapi-platform \
  -o jsonpath='{.spec.template.spec.containers[*].name}'
```

### Frontend circular import / TDZ errors

If you see `ReferenceError: can't access lexical declaration 'X' before initialization`
in the browser console after a frontend build, it's likely a circular ESM import.

`API_URL` was extracted to `frontend/src/config.js` specifically to break a circular
dependency chain (App.jsx -> Dashboard -> LogsPanel -> API_URL from App.jsx). All
files import `API_URL` from `config.js`, not from `App.jsx`.

### Testing runner changes without redeploying user apps

To test request logging or other runner middleware, exec into a running user app pod:

```bash
# curl isn't available in the slim Python image, use httpx instead
kubectl exec -n fastapi-platform deployment/app-XXXXX -- \
  python3 -c "import httpx; print(httpx.get('http://localhost:8000/').status_code)"
```

### Checking runner logs

```bash
# Backend logs
kubectl logs -n fastapi-platform deployment/backend --tail=50

# User app logs (look for "Request logging enabled", "Static files mounted", etc.)
kubectl logs -n fastapi-platform deployment/app-XXXXX --tail=50
```

## Quick Reference

```bash
# Full rebuild and deploy cycle
docker build -t ghcr.io/thatcatxedo/fastapi-platform-backend:dev backend/ && \
docker build -t ghcr.io/thatcatxedo/fastapi-platform-frontend:dev frontend/ && \
docker build -t ghcr.io/thatcatxedo/fastapi-platform-runner:dev runner/ && \
k3d image import \
  ghcr.io/thatcatxedo/fastapi-platform-backend:dev \
  ghcr.io/thatcatxedo/fastapi-platform-frontend:dev \
  ghcr.io/thatcatxedo/fastapi-platform-runner:dev \
  -c fastapi-platform-dev && \
kubectl rollout restart deployment/backend deployment/frontend -n fastapi-platform && \
kubectl rollout status deployment/backend deployment/frontend -n fastapi-platform

# Check everything is healthy
kubectl get pods -n fastapi-platform

# Tail all platform logs
kubectl logs -n fastapi-platform deployment/backend -f
```
