# Deployment (Kustomize)

The platform owns its deployment manifests in `deploy/`.

## Prerequisites

- Traefik + CRDs installed (`IngressRoute`, `Middleware`)
- `platform-secrets` secret in `fastapi-platform` namespace
  - `MONGO_URI`
  - `SECRET_KEY`
- `ghcr-auth` image pull secret in `fastapi-platform`

## Apply an overlay

Local:
```
kubectl apply -k deploy/overlays/local
```

Prod:
```
kubectl apply -k deploy/overlays/prod
```

## Notes

- `BASE_DOMAIN` is patched per overlay.
- `RUNNER_IMAGE` and `PLATFORM_NAMESPACE` can be overridden via overlays.
