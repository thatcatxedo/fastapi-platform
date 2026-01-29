# Platform deployment (Kustomize)

This directory will own the platform manifests and Kustomize overlays.

Planned layout:
```
deploy/
  base/
    kustomization.yaml
    namespace.yaml
    rbac.yaml
    backend-deployment.yaml
    backend-service.yaml
    frontend-deployment.yaml
    frontend-service.yaml
    ingressroutes.yaml
  overlays/
    local/
    prod/
```

Until these manifests are added, the platform remains deployed via the
`homelab-cluster` repo.
