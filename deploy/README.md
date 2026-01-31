# Platform Deployment (Kustomize)

This directory contains the platform manifests and Kustomize overlays.

## Structure

```
deploy/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── rbac.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   └── ingressroutes.yaml
└── overlays/
    ├── local/
    └── homelab/
```

## Prerequisites

Before deploying, ensure:
1. Traefik + CRDs installed (`IngressRoute`, `Middleware`)
2. `platform-secrets` secret exists with `MONGO_URI` and `SECRET_KEY`
3. `ghcr-auth` image pull secret exists for pulling runner images

## Quick Deploy

Use the root `deploy.sh` script for automated deployment:

```bash
./deploy.sh        # Deploy to homelab (default)
./undeploy.sh      # Tear down
```

## Manual Kustomize Apply

Local development:
```bash
kubectl apply -k deploy/overlays/local
```

Homelab:
```bash
kubectl apply -k deploy/overlays/homelab
```

## Configuration

Environment-specific patches are in the overlays. Key variables:
- `BASE_DOMAIN` - Platform UI domain
- `APP_DOMAIN` - User app subdomain base
- `RUNNER_IMAGE` - Container image for user apps
- `PLATFORM_NAMESPACE` - Target namespace
