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
    log_info "Loading configuration from .env"
    set -a
    source .env
    set +a
fi

# Configuration with defaults
ENVIRONMENT="${ENVIRONMENT:-local}"
DOMAIN="${DOMAIN:-localhost}"
NAMESPACE="fastapi-platform"
CLUSTER_FOUNDATION_DIR="${CLUSTER_FOUNDATION_DIR:-../fastapi-platform-cluster-foundation}"

log_info "========================================"
log_info "FastAPI Platform Deployment"
log_info "========================================"
log_info "Environment: ${ENVIRONMENT}"
log_info "Domain: ${DOMAIN}"
log_info "Namespace: ${NAMESPACE}"
log_info "========================================"

# ------------------------------------------------------------------------------
# Step 1: Check prerequisites
# ------------------------------------------------------------------------------
log_info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed. Install it with: brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    log_error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

log_success "Prerequisites OK"

# ------------------------------------------------------------------------------
# Step 2: Check if cluster-foundation is running
# ------------------------------------------------------------------------------
log_info "Checking cluster status..."

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    log_warn "No Kubernetes cluster found"

    if [ -d "$CLUSTER_FOUNDATION_DIR" ]; then
        log_info "Found cluster-foundation at: $CLUSTER_FOUNDATION_DIR"
        echo -n "Do you want to run cluster-foundation setup? (y/N): "
        read -r response
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
        if [ "$response" = "y" ] || [ "$response" = "yes" ]; then
            log_info "Running cluster-foundation setup..."
            cd "$CLUSTER_FOUNDATION_DIR"
            ./setup.sh
            cd "$SCRIPT_DIR"
        else
            log_error "Cannot proceed without a running cluster"
            exit 1
        fi
    else
        log_error "No cluster-foundation found at: $CLUSTER_FOUNDATION_DIR"
        log_error "Please set up a Kubernetes cluster first"
        exit 1
    fi
fi

# Check for required components
log_info "Checking for Traefik..."
if ! kubectl get deployment -n traefik traefik &> /dev/null; then
    log_error "Traefik not found. Please run cluster-foundation setup first."
    exit 1
fi

log_info "Checking for MongoDB..."
if ! kubectl get statefulset -n mongodb mongodb &> /dev/null; then
    log_error "MongoDB not found. Please run cluster-foundation setup first."
    exit 1
fi

log_success "Cluster foundation is running"

# ------------------------------------------------------------------------------
# Step 3: Get GHCR token with read:packages scope
# ------------------------------------------------------------------------------
log_info "Getting GHCR authentication token..."

# Check if current token has read:packages scope
TOKEN_SCOPES=$(gh auth status 2>&1 | grep "Token scopes" || echo "")
if ! echo "$TOKEN_SCOPES" | grep -qE "(read|write):packages"; then
    log_warn "GitHub token missing read:packages or write:packages scope"
    log_info "Requesting additional scope (you may be prompted to authenticate)..."
    gh auth refresh -s read:packages
fi

GHCR_TOKEN=$(gh auth token 2>/dev/null || true)
if [ -z "$GHCR_TOKEN" ]; then
    log_error "Failed to get GitHub token. Make sure you're authenticated: gh auth login"
    exit 1
fi

GITHUB_USER=$(gh api user --jq .login 2>/dev/null || true)
if [ -z "$GITHUB_USER" ]; then
    log_error "Failed to get GitHub username"
    exit 1
fi

log_success "Got GHCR credentials for: $GITHUB_USER"

# ------------------------------------------------------------------------------
# Step 4: Create namespace
# ------------------------------------------------------------------------------
log_info "Creating namespace: ${NAMESPACE}"

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

log_success "Namespace ready"

# ------------------------------------------------------------------------------
# Step 5: Build MongoDB URI from cluster-foundation secrets
# ------------------------------------------------------------------------------
log_info "Building MongoDB connection string..."

# Get MongoDB password from cluster-foundation secrets
MONGO_PASSWORD=$(kubectl get secret -n mongodb mongodb-secrets -o jsonpath='{.data.MONGODB_APP_PASSWORD}' 2>/dev/null | base64 -d || echo "")

if [ -z "$MONGO_PASSWORD" ]; then
    log_warn "Could not get MongoDB password from secrets, using default"
    MONGO_PASSWORD="platformpass456"
fi

MONGO_URI="mongodb://platform:${MONGO_PASSWORD}@mongodb.mongodb.svc.cluster.local:27017/fastapi_platform_db?authSource=platform"
log_success "MongoDB URI configured"

# ------------------------------------------------------------------------------
# Step 6: Generate SECRET_KEY if not provided
# ------------------------------------------------------------------------------
if [ -z "$SECRET_KEY" ]; then
    log_info "Generating random SECRET_KEY..."
    SECRET_KEY=$(openssl rand -hex 32)
fi

# ------------------------------------------------------------------------------
# Step 7: Create platform-secrets
# ------------------------------------------------------------------------------
log_info "Creating platform-secrets..."

kubectl create secret generic platform-secrets \
    --namespace="${NAMESPACE}" \
    --from-literal=MONGO_URI="${MONGO_URI}" \
    --from-literal=SECRET_KEY="${SECRET_KEY}" \
    --dry-run=client -o yaml | kubectl apply -f -

log_success "platform-secrets created"

# ------------------------------------------------------------------------------
# Step 8: Create GHCR auth secret
# ------------------------------------------------------------------------------
log_info "Creating GHCR authentication secret..."

kubectl create secret docker-registry ghcr-auth \
    --namespace="${NAMESPACE}" \
    --docker-server=ghcr.io \
    --docker-username="${GITHUB_USER}" \
    --docker-password="${GHCR_TOKEN}" \
    --dry-run=client -o yaml | kubectl apply -f -

log_success "ghcr-auth secret created"

# ------------------------------------------------------------------------------
# Step 9: Apply Kustomize overlay
# ------------------------------------------------------------------------------
log_info "Applying Kustomize overlay: ${ENVIRONMENT}"

OVERLAY_PATH="deploy/overlays/${ENVIRONMENT}"

if [ ! -d "$OVERLAY_PATH" ]; then
    log_error "Overlay not found: $OVERLAY_PATH"
    log_info "Available overlays:"
    ls -1 deploy/overlays/
    exit 1
fi

kubectl apply -k "$OVERLAY_PATH"

log_success "Manifests applied"

# ------------------------------------------------------------------------------
# Step 10: Wait for deployments
# ------------------------------------------------------------------------------
log_info "Waiting for deployments to be ready..."

# Wait for backend
log_info "Waiting for backend deployment..."
if kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=120s; then
    log_success "Backend is ready"
else
    log_error "Backend deployment failed"
    kubectl describe deployment/backend -n "${NAMESPACE}"
    kubectl logs deployment/backend -n "${NAMESPACE}" --tail=50 || true
    exit 1
fi

# Wait for frontend
log_info "Waiting for frontend deployment..."
if kubectl rollout status deployment/frontend -n "${NAMESPACE}" --timeout=120s; then
    log_success "Frontend is ready"
else
    log_error "Frontend deployment failed"
    kubectl describe deployment/frontend -n "${NAMESPACE}"
    kubectl logs deployment/frontend -n "${NAMESPACE}" --tail=50 || true
    exit 1
fi

# ------------------------------------------------------------------------------
# Step 11: Validate and show status
# ------------------------------------------------------------------------------
log_info "Validating deployment..."

echo ""
log_info "Pod Status:"
kubectl get pods -n "${NAMESPACE}"

echo ""
log_info "Services:"
kubectl get services -n "${NAMESPACE}"

echo ""
log_info "IngressRoutes:"
kubectl get ingressroutes -n "${NAMESPACE}" 2>/dev/null || log_warn "No IngressRoutes found"

# ------------------------------------------------------------------------------
# Step 12: Print access information
# ------------------------------------------------------------------------------
echo ""
log_success "========================================"
log_success "Deployment Complete!"
log_success "========================================"

if [ "$ENVIRONMENT" = "local" ]; then
    log_info "Access the platform at: http://localhost"
    log_info "API at: http://localhost/api"
elif [ "$ENVIRONMENT" = "homelab" ]; then
    log_info "Access the platform at: https://platform.${DOMAIN}"
    log_info "API at: https://platform.${DOMAIN}/api"
else
    log_info "Access the platform at: https://platform.${DOMAIN}"
    log_info "API at: https://platform.${DOMAIN}/api"
fi

echo ""
log_info "Useful commands:"
log_info "  kubectl get pods -n ${NAMESPACE}"
log_info "  kubectl logs -n ${NAMESPACE} deployment/backend"
log_info "  kubectl logs -n ${NAMESPACE} deployment/frontend"
