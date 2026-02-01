# Claude AI Integration

This document explains how the AI chat feature integrates Claude to help users build and manage FastAPI/FastHTML applications.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │ Chat Page   │───▶│ useChat.js  │───▶│ SSE Stream Reader               │  │
│  │ AppSelector │    │ (hook)      │    │ Parses: text, tool_start,       │  │
│  └─────────────┘    └─────────────┘    │         tool_result, done       │  │
│                                        └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ POST /api/chat/conversations/{id}/messages
                                    │ Body: { content, app_id? }
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI)                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────────────┐   │
│  │ routers/chat.py │───▶│ chat/service.py │───▶│ chat/tools.py         │   │
│  │                 │    │                 │    │                       │   │
│  │ - Auth check    │    │ - Build system  │    │ - create_app          │   │
│  │ - Stream resp   │    │   prompt        │    │ - update_app          │   │
│  │                 │    │ - Call n8n      │    │ - get_app             │   │
│  │                 │    │ - Execute tools │    │ - get_app_logs        │   │
│  │                 │    │ - Stream SSE    │    │ - list_apps           │   │
│  └─────────────────┘    └─────────────────┘    │ - delete_app          │   │
│                                                │ - list_databases      │   │
│                                                └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ POST http://n8n.localhost/webhook/chat
                                    │ Body: { messages, system_prompt, tools, user_id }
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              n8n Workflow                                    │
│  ┌─────────────┐    ┌─────────────────────┐    ┌───────────────────────┐   │
│  │ Webhook     │───▶│ Call Claude API     │───▶│ Format Response       │   │
│  │ Trigger     │    │ (Anthropic node)    │    │ as JSON array         │   │
│  └─────────────┘    └─────────────────────┘    └───────────────────────┘   │
│                                                                              │
│  Returns: [{"type":"text","content":"..."}, {"type":"tool_call",...}, ...]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend Chat UI

**Files:**
- `frontend/src/pages/Chat/index.jsx` - Main chat page
- `frontend/src/hooks/useChat.js` - Chat state and SSE handling
- `frontend/src/pages/Chat/components/AppSelector.jsx` - App context selector

**Key Features:**
- Conversation list sidebar
- Message streaming with typing indicator
- Tool execution status display
- App context selector (dropdown to select which app you're working on)

### 2. Backend Chat Service

**Files:**
- `backend/routers/chat.py` - API endpoints
- `backend/chat/service.py` - Core chat logic
- `backend/chat/tools.py` - Tool definitions and execution
- `backend/chat/models.py` - Pydantic models

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/conversations` | Create conversation |
| GET | `/api/chat/conversations` | List conversations |
| GET | `/api/chat/conversations/{id}` | Get conversation with messages |
| DELETE | `/api/chat/conversations/{id}` | Delete conversation |
| POST | `/api/chat/conversations/{id}/messages` | Send message (SSE stream) |

### 3. n8n Workflow

**Location:** Kubernetes deployment in `fastapi-platform` namespace

**Access:**
- Internal: `http://n8n.fastapi-platform.svc.cluster.local:5678`
- Local dev: `http://n8n.localhost` (requires `/etc/hosts` entry)

**Workflow:** `chat-workflow.json` in `n8n-workflows/`

The workflow:
1. Receives webhook POST with messages, system prompt, and tools
2. Calls Anthropic Claude API with tool definitions
3. Returns JSON array of events

## Message Flow

### 1. User Sends Message

```javascript
// Frontend sends POST request
POST /api/chat/conversations/{id}/messages
{
  "content": "Add a /health endpoint to my app",
  "app_id": "abc123"  // Optional - for context awareness
}
```

### 2. Backend Builds Context

```python
# chat/service.py - _build_system_prompt()
system_prompt = f"""
You are an AI assistant helping users build FastAPI/FastHTML apps.

User Context:
- User ID: {user_id}
- Username: {username}

Current App Context:  # Only if app_id provided
- App ID: abc123
- Name: my-api
- Status: running
- URL: https://app-abc123.gatorlunch.com

Current code:
```python
from fastapi import FastAPI
app = FastAPI()
# ... existing code ...
```

IMPORTANT: When the user refers to "the app", use update_app with the app_id above.
"""
```

### 3. n8n Calls Claude

The backend POSTs to n8n webhook:
```json
{
  "messages": [
    {"role": "user", "content": "Add a /health endpoint"}
  ],
  "system_prompt": "You are an AI assistant...",
  "tools": [...],
  "user_id": "697ec1edc5ea12f9e091a324"
}
```

### 4. Claude Responds with Tool Call

n8n returns:
```json
[
  {"type": "text", "content": "I'll add a /health endpoint to your app."},
  {"type": "tool_call", "name": "update_app", "input": {"app_id": "abc123", "code": "..."}},
  {"type": "done"}
]
```

### 5. Backend Executes Tool

```python
# chat/service.py - processes tool_call events
tool_result = await execute_tool("update_app", {"app_id": "abc123", "code": "..."}, user)
# Returns: {"success": true, "url": "https://app-abc123.gatorlunch.com", ...}
```

### 6. Frontend Receives SSE Stream

```
data: {"type": "text", "content": "I'll add a /health endpoint..."}

data: {"type": "tool_start", "tool": "update_app", "tool_input": {...}}

data: {"type": "tool_result", "tool": "update_app", "result": {"success": true, ...}}

data: {"type": "done"}
```

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_app` | Create and deploy a new app | `name`, `code` or `files`, `framework?`, `database_id?` |
| `update_app` | Update existing app code | `app_id`, `code` or `files`, `name?` |
| `get_app` | Get app details including code | `app_id` |
| `get_app_logs` | Fetch pod logs for debugging | `app_id`, `tail_lines?` |
| `list_apps` | List all user's apps | (none) |
| `delete_app` | Delete an app | `app_id` |
| `list_databases` | List user's databases | (none) |

## App Context Awareness

The chat can be "attached" to a specific app for context-aware assistance:

### How It Works

1. **User selects app** via dropdown in chat UI or URL param (`/chat?app=abc123`)
2. **Frontend sends app_id** with each message
3. **Backend fetches app details** from MongoDB
4. **System prompt includes:**
   - App ID, name, status, URL
   - Current code (truncated if >3000 chars)
   - File list for multi-file apps
5. **Claude knows** to use `update_app` instead of `create_app`

### From Editor

The Editor has a "Chat about this app" option in the More dropdown that navigates to `/chat?app={appId}`, pre-selecting that app in the chat.

## n8n Workflow Details

**File:** `n8n-workflows/chat-workflow.json`

The workflow has 4 nodes:

```
Webhook ──▶ Call Claude API ──▶ Process Response ──▶ Respond to Webhook
```

### 1. Webhook Trigger
- Listens on `POST /webhook/chat`
- Receives: `{ messages, system_prompt, tools, user_id }`

### 2. Call Claude API
- POSTs to `https://api.anthropic.com/v1/messages`
- Uses `claude-sonnet-4-20250514` model
- Max tokens: 4096
- Headers: `x-api-key`, `anthropic-version: 2023-06-01`
- Body constructed from webhook input (system, messages, tools)

### 3. Process Response (JavaScript Code Node)
```javascript
// Transforms Claude API response to our event format
const response = $input.first().json;
const results = [];

for (const block of response.content) {
  if (block.type === 'text') {
    results.push({ json: { type: 'text', content: block.text } });
  } else if (block.type === 'tool_use') {
    results.push({
      json: {
        type: 'tool_call',
        id: block.id,
        name: block.name,
        input: block.input
      }
    });
  }
}

results.push({ json: { type: 'done', stop_reason: response.stop_reason } });
return results;
```

### 4. Respond to Webhook
- Returns all items as JSON array
- Content-Type: `application/json`

### Response Format

n8n returns a JSON array (not newline-delimited):
```json
[
  {"type": "text", "content": "I'll help you..."},
  {"type": "tool_call", "id": "toolu_01...", "name": "create_app", "input": {...}},
  {"type": "done", "stop_reason": "tool_use"}
]
```

The backend handles this by iterating over the array items.

## n8n Setup

### Environment Variables

```yaml
# deploy/base/n8n-deployment.yaml
- name: ANTHROPIC_API_KEY
  valueFrom:
    secretKeyRef:
      name: platform-secrets
      key: ANTHROPIC_API_KEY
- name: N8N_BLOCK_ENV_ACCESS_IN_NODE
  value: "false"  # Allow env vars in expressions
- name: N8N_SECURE_COOKIE
  value: "false"  # Allow HTTP access locally
```

### Workflow Management

```bash
# Helper script for workflow operations
./scripts/n8n-helper.sh status          # Check n8n status
./scripts/n8n-helper.sh logs            # View n8n logs
./scripts/n8n-helper.sh sync            # Sync workflow from JSON
./scripts/n8n-helper.sh workflow-detail # View workflow details
```

### Persistence

n8n uses a PVC for data persistence:
- Workflows persist across pod restarts
- API keys stored in n8n's encrypted storage
- License activates automatically via `N8N_LICENSE_ACTIVATION_KEY`

## SSE Event Types

| Type | Description | Fields |
|------|-------------|--------|
| `text` | Streamed text content | `content` |
| `tool_start` | Tool execution starting | `tool`, `tool_input` |
| `tool_result` | Tool completed | `tool`, `result` |
| `done` | Response complete | (none) |
| `error` | Error occurred | `error` |

## Database Collections

**conversations:**
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  title: string | null,
  created_at: datetime,
  updated_at: datetime,
  message_count: number
}
```

**messages:**
```javascript
{
  _id: ObjectId,
  conversation_id: ObjectId,
  role: "user" | "assistant",
  content: string,
  tool_calls: [{
    id: string,
    name: string,
    input: object,
    result: object
  }] | null,
  created_at: datetime
}
```

## Future Improvements

See `docs/ROADMAP.md` Phase 5 for planned enhancements:

- [ ] BYOK (Bring Your Own Key) - users provide their own API keys
- [ ] Multi-provider support (OpenAI, etc.)
- [ ] Platform-aware prompts with constraints
- [ ] Safety model with diff view for AI-generated code
- [ ] Rate limiting per user
