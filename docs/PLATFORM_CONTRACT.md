# Platform Contract

This document defines what a Kubernetes cluster must provide in order to run
`fastapi-platform`.

## Required cluster components

- Kubernetes (k3s is fine)
- Traefik ingress controller
- Traefik CRDs: `IngressRoute`, `Middleware`
- MongoDB accessible from the platform namespace

## Required namespaces

- `fastapi-platform` (platform resources)
- `traefik` (ingress controller)

## Required secrets (platform namespace)

- `platform-secrets`
  - `SECRET_KEY` (JWT signing)
  - `MONGO_URI` (MongoDB connection string)
- `ghcr-auth`
  - `.dockerconfigjson` (for pulling runner images)

## Required environment variables

- `PLATFORM_NAMESPACE` (default: `fastapi-platform`)
- `RUNNER_IMAGE` (default: GHCR runner image)
- `BASE_DOMAIN` (default: `platform.gofastapi.xyz`) - Platform UI domain
- `APP_DOMAIN` (default: `gatorlunch.com`) - User app subdomain base (apps at `app-{id}.{APP_DOMAIN}`)

## Required permissions (platform ServiceAccount)

- Create/read/update/delete:
  - Deployments
  - Services
  - ConfigMaps
  - Traefik `IngressRoute` and `Middleware` resources

## Optional components

- cert-manager (TLS automation if not using Cloudflare Tunnel)
- cloudflared (public access via Cloudflare Tunnel)
- Flux (GitOps deployment)
