#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Configuration with defaults
ENVIRONMENT="${ENVIRONMENT:-local}"
NAMESPACE="fastapi-platform"

log_info "========================================"
log_info "FastAPI Platform Undeployment"
log_info "========================================"
log_info "Environment: ${ENVIRONMENT}"
log_info "Namespace: ${NAMESPACE}"
log_info "========================================"

# Confirm
echo -n "Are you sure you want to undeploy the platform? (y/N): "
read -r confirm
confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')
if [ "$confirm" != "y" ] && [ "$confirm" != "yes" ]; then
    log_info "Cancelled"
    exit 0
fi

# Check if namespace exists
if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    log_warn "Namespace ${NAMESPACE} does not exist"
    exit 0
fi

# Delete Kustomize resources
OVERLAY_PATH="deploy/overlays/${ENVIRONMENT}"
if [ -d "$OVERLAY_PATH" ]; then
    log_info "Deleting Kustomize resources from: ${OVERLAY_PATH}"
    kubectl delete -k "$OVERLAY_PATH" --ignore-not-found=true || true
else
    log_warn "Overlay not found: $OVERLAY_PATH"
fi

# Delete secrets
log_info "Deleting secrets..."
kubectl delete secret platform-secrets -n "${NAMESPACE}" --ignore-not-found=true || true
kubectl delete secret ghcr-auth -n "${NAMESPACE}" --ignore-not-found=true || true

# Delete any user-deployed apps (ConfigMaps, Deployments, Services, IngressRoutes)
log_info "Cleaning up any user-deployed apps..."
kubectl delete deployments -n "${NAMESPACE}" -l app.kubernetes.io/managed-by=fastapi-platform --ignore-not-found=true || true
kubectl delete services -n "${NAMESPACE}" -l app.kubernetes.io/managed-by=fastapi-platform --ignore-not-found=true || true
kubectl delete configmaps -n "${NAMESPACE}" -l app.kubernetes.io/managed-by=fastapi-platform --ignore-not-found=true || true
kubectl delete ingressroutes -n "${NAMESPACE}" -l app.kubernetes.io/managed-by=fastapi-platform --ignore-not-found=true || true
kubectl delete middlewares -n "${NAMESPACE}" -l app.kubernetes.io/managed-by=fastapi-platform --ignore-not-found=true || true

# Optional: Delete namespace
echo -n "Delete namespace ${NAMESPACE}? (y/N): "
read -r delete_ns
delete_ns=$(echo "$delete_ns" | tr '[:upper:]' '[:lower:]')
if [ "$delete_ns" = "y" ] || [ "$delete_ns" = "yes" ]; then
    log_info "Deleting namespace: ${NAMESPACE}"
    kubectl delete namespace "${NAMESPACE}" --ignore-not-found=true || true
fi

log_success "========================================"
log_success "Platform undeployed successfully"
log_success "========================================"
log_info "Note: MongoDB and Traefik (cluster-foundation) are still running"
log_info "To destroy everything, run: cd ../fastapi-platform-cluster-foundation && ./destroy.sh"
