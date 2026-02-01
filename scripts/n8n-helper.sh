#!/bin/bash
# n8n Workflow Management Helper
# Usage: ./scripts/n8n-helper.sh <command> [args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Configuration
NAMESPACE="${NAMESPACE:-fastapi-platform}"
N8N_API_KEY="${N8N_API_KEY:-}"

# Get n8n URL - prefer local hostname via Traefik, fallback to port-forward
get_n8n_url() {
    if [ -n "$N8N_URL" ]; then
        echo "$N8N_URL"
    elif curl -s --connect-timeout 1 -H "Host: n8n.localhost" http://127.0.0.1/healthz > /dev/null 2>&1; then
        # n8n.localhost available via Traefik (no port-forward needed)
        echo "http://n8n.localhost"
    else
        # Fallback to port-forward
        echo "http://localhost:5678"
    fi
}

# Start port-forward in background (only if n8n.localhost not available)
start_port_forward() {
    # Skip if n8n.localhost is available via Traefik
    if curl -s --connect-timeout 1 -H "Host: n8n.localhost" http://127.0.0.1/healthz > /dev/null 2>&1; then
        return 0
    fi
    # Check if already forwarding
    if pgrep -f "kubectl port-forward.*n8n.*5678" > /dev/null; then
        return 0
    fi
    kubectl port-forward -n "$NAMESPACE" svc/n8n 5678:5678 > /dev/null 2>&1 &
    PF_PID=$!
    sleep 2
    echo $PF_PID
}

# Stop port-forward (only if we started one)
stop_port_forward() {
    # Don't kill if using n8n.localhost
    if curl -s --connect-timeout 1 -H "Host: n8n.localhost" http://127.0.0.1/healthz > /dev/null 2>&1; then
        return 0
    fi
    pkill -f "kubectl port-forward.*n8n.*5678" 2>/dev/null || true
}

# API call helper
n8n_api() {
    local method="$1"
    local endpoint="$2"
    local data="$3"

    local url="$(get_n8n_url)/api/v1${endpoint}"

    if [ -z "$N8N_API_KEY" ]; then
        echo "Error: N8N_API_KEY not set. Add it to .env" >&2
        exit 1
    fi

    if [ -n "$data" ]; then
        curl -s -X "$method" "$url" \
            -H "X-N8N-API-KEY: $N8N_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$url" \
            -H "X-N8N-API-KEY: $N8N_API_KEY"
    fi
}

# List workflows
cmd_workflows() {
    start_port_forward
    echo "Workflows:"
    n8n_api GET "/workflows" | jq -r '.data[] | "\(.id) | \(.name) | active=\(.active)"'
    stop_port_forward
}

# Update or create workflow from file
cmd_update_workflow() {
    local file="$1"
    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo "Usage: $0 update-workflow <workflow.json>"
        exit 1
    fi

    local workflow_name=$(jq -r '.name' "$file")
    echo "Syncing workflow: $workflow_name"

    start_port_forward

    # Find existing workflow by name
    local existing_id=$(n8n_api GET "/workflows" | jq -r ".data[] | select(.name==\"${workflow_name}\") | .id" | head -1)

    if [ -n "$existing_id" ] && [ "$existing_id" != "null" ]; then
        echo "Updating existing workflow (ID: $existing_id)"
        n8n_api PUT "/workflows/${existing_id}" "$(cat "$file")" > /dev/null

        # Deactivate then reactivate to ensure webhook registration
        n8n_api POST "/workflows/${existing_id}/deactivate" > /dev/null 2>&1 || true
        n8n_api POST "/workflows/${existing_id}/activate" > /dev/null
        echo "Workflow updated and activated"
    else
        echo "Creating new workflow"
        local new_id=$(n8n_api POST "/workflows" "$(cat "$file")" | jq -r '.id')
        if [ -n "$new_id" ] && [ "$new_id" != "null" ]; then
            n8n_api POST "/workflows/${new_id}/activate" > /dev/null
            echo "Workflow created (ID: $new_id) and activated"
        else
            echo "Failed to create workflow"
            exit 1
        fi
    fi

    stop_port_forward
}

# Activate workflow by ID or name
cmd_activate() {
    local id_or_name="$1"
    if [ -z "$id_or_name" ]; then
        echo "Usage: $0 activate <workflow_id_or_name>"
        exit 1
    fi

    start_port_forward

    # Check if it's a name, find ID
    local workflow_id="$id_or_name"
    if ! [[ "$id_or_name" =~ ^[a-zA-Z0-9]{16,}$ ]]; then
        workflow_id=$(n8n_api GET "/workflows" | jq -r ".data[] | select(.name==\"${id_or_name}\") | .id" | head -1)
    fi

    if [ -z "$workflow_id" ] || [ "$workflow_id" = "null" ]; then
        echo "Workflow not found: $id_or_name"
        exit 1
    fi

    n8n_api POST "/workflows/${workflow_id}/activate" > /dev/null
    echo "Activated workflow: $workflow_id"

    stop_port_forward
}

# Deactivate workflow
cmd_deactivate() {
    local id_or_name="$1"
    if [ -z "$id_or_name" ]; then
        echo "Usage: $0 deactivate <workflow_id_or_name>"
        exit 1
    fi

    start_port_forward

    local workflow_id="$id_or_name"
    if ! [[ "$id_or_name" =~ ^[a-zA-Z0-9]{16,}$ ]]; then
        workflow_id=$(n8n_api GET "/workflows" | jq -r ".data[] | select(.name==\"${id_or_name}\") | .id" | head -1)
    fi

    if [ -z "$workflow_id" ] || [ "$workflow_id" = "null" ]; then
        echo "Workflow not found: $id_or_name"
        exit 1
    fi

    n8n_api POST "/workflows/${workflow_id}/deactivate" > /dev/null
    echo "Deactivated workflow: $workflow_id"

    stop_port_forward
}

# Sync all workflows from n8n-workflows directory
cmd_sync_workflows() {
    local workflows_dir="$PROJECT_DIR/n8n-workflows"

    if [ ! -d "$workflows_dir" ]; then
        echo "No n8n-workflows directory found"
        exit 1
    fi

    echo "Syncing workflows from $workflows_dir..."

    # Sync all workflow JSON files
    local count=0
    for workflow_file in "$workflows_dir"/*.json; do
        if [ -f "$workflow_file" ]; then
            cmd_update_workflow "$workflow_file"
            count=$((count + 1))
        fi
    done

    if [ $count -eq 0 ]; then
        echo "No workflow files found"
    else
        echo "Synced $count workflow(s)"
    fi
}

# List recent executions
cmd_executions() {
    local limit="${1:-10}"
    start_port_forward
    echo "Recent executions:"
    n8n_api GET "/executions?limit=$limit" | jq -r '.data[] | "\(.id) | \(.workflowId) | \(.status) | \(.startedAt)"' 2>/dev/null || echo "No executions found"
    stop_port_forward
}

# Show n8n status
cmd_status() {
    start_port_forward
    echo "=== n8n Status ==="

    # Check health
    local health=$(curl -s -o /dev/null -w "%{http_code}" "$(get_n8n_url)/healthz")
    echo "Health: $health"

    # List workflows with status
    echo ""
    echo "Workflows:"
    n8n_api GET "/workflows" | jq -r '.data[] | "  \(.name): active=\(.active) id=\(.id)"' 2>/dev/null || echo "  (none or API error)"

    # Recent executions
    echo ""
    echo "Recent executions (last 5):"
    n8n_api GET "/executions?limit=5" | jq -r '.data[] | "  \(.id) | \(.status) | \(.startedAt)"' 2>/dev/null || echo "  (none)"

    stop_port_forward
}

# Tail n8n logs
cmd_logs() {
    local lines="${1:-50}"
    kubectl logs -n "$NAMESPACE" deployment/n8n --tail="$lines" -f
}

# Get workflow details
cmd_workflow_detail() {
    local id_or_name="$1"
    if [ -z "$id_or_name" ]; then
        echo "Usage: $0 workflow-detail <workflow_id_or_name>"
        exit 1
    fi

    start_port_forward

    local workflow_id="$id_or_name"
    if ! [[ "$id_or_name" =~ ^[a-zA-Z0-9]{16,}$ ]]; then
        workflow_id=$(n8n_api GET "/workflows" | jq -r ".data[] | select(.name==\"${id_or_name}\") | .id" | head -1)
    fi

    if [ -z "$workflow_id" ] || [ "$workflow_id" = "null" ]; then
        echo "Workflow not found: $id_or_name"
        exit 1
    fi

    n8n_api GET "/workflows/${workflow_id}" | jq '.'
    stop_port_forward
}

# Delete workflow
cmd_delete_workflow() {
    local id_or_name="$1"
    if [ -z "$id_or_name" ]; then
        echo "Usage: $0 delete-workflow <workflow_id_or_name>"
        exit 1
    fi

    start_port_forward

    local workflow_id="$id_or_name"
    if ! [[ "$id_or_name" =~ ^[a-zA-Z0-9]{16,}$ ]]; then
        workflow_id=$(n8n_api GET "/workflows" | jq -r ".data[] | select(.name==\"${id_or_name}\") | .id" | head -1)
    fi

    if [ -z "$workflow_id" ] || [ "$workflow_id" = "null" ]; then
        echo "Workflow not found: $id_or_name"
        exit 1
    fi

    # Deactivate first
    n8n_api POST "/workflows/${workflow_id}/deactivate" > /dev/null 2>&1 || true
    n8n_api DELETE "/workflows/${workflow_id}" > /dev/null
    echo "Deleted workflow: $workflow_id"
    stop_port_forward
}

# Get execution detail
cmd_execution_detail() {
    local exec_id="$1"
    if [ -z "$exec_id" ]; then
        echo "Usage: $0 execution-detail <execution_id>"
        exit 1
    fi

    start_port_forward
    n8n_api GET "/executions/${exec_id}" | jq '.'
    stop_port_forward
}

# Test webhook
cmd_test_webhook() {
    local path="${1:-chat}"
    shift
    local payload="${*:-{\"messages\":[{\"role\":\"user\",\"content\":\"Say hello\"}],\"tools\":[]}}"

    start_port_forward
    echo "Testing webhook: /webhook/$path"
    echo "Payload: $payload"
    echo ""

    local response
    local http_code
    response=$(curl -s -w "\n%{http_code}" -X POST "$(get_n8n_url)/webhook/$path" \
        -H "Content-Type: application/json" \
        --data-raw "$payload" --max-time 30)

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    echo "HTTP Status: $http_code"
    echo "Response:"
    if [ -n "$body" ]; then
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo "(empty response)"
    fi
    stop_port_forward
}

# Show help
cmd_help() {
    cat << EOF
n8n Workflow Management Helper

Usage: $0 <command> [args]

Commands:
  status                 Show n8n health, workflows, and recent executions
  workflows              List all workflows
  workflow-detail ID     Get workflow details (nodes, settings)
  update-workflow FILE   Create or update workflow from JSON file
  delete-workflow ID     Delete a workflow
  activate ID|NAME       Activate a workflow
  deactivate ID|NAME     Deactivate a workflow
  sync-workflows         Sync all workflows from n8n-workflows/
  executions [N]         List recent N executions (default: 10)
  execution-detail ID    Get execution details
  test-webhook [PATH]    Test webhook (default: chat)
  logs [N]               Tail n8n pod logs (default: 50 lines)

Environment:
  N8N_API_KEY           Required. n8n API key for authentication
  NAMESPACE             Kubernetes namespace (default: fastapi-platform)

Examples:
  $0 status
  $0 workflows
  $0 update-workflow n8n-workflows/chat-workflow.json
  $0 activate "Platform Chat"
  $0 test-webhook chat '{"messages":[{"role":"user","content":"hi"}]}'
  $0 logs 100
EOF
}

# Main
case "${1:-help}" in
    status) cmd_status ;;
    workflows) cmd_workflows ;;
    workflow-detail) cmd_workflow_detail "$2" ;;
    update-workflow) cmd_update_workflow "$2" ;;
    delete-workflow) cmd_delete_workflow "$2" ;;
    activate) cmd_activate "$2" ;;
    deactivate) cmd_deactivate "$2" ;;
    sync-workflows) cmd_sync_workflows ;;
    executions) cmd_executions "$2" ;;
    execution-detail) cmd_execution_detail "$2" ;;
    test-webhook) shift; cmd_test_webhook "$@" ;;
    logs) cmd_logs "$2" ;;
    help|--help|-h) cmd_help ;;
    *) echo "Unknown command: $1"; cmd_help; exit 1 ;;
esac
