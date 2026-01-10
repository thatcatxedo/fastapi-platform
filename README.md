# FastAPI Learning Platform

A multi-tenant platform where users can write FastAPI code in a web editor and deploy it as isolated Kubernetes applications.

## How It Works

### User Flow

1. **Sign Up / Login**: Users authenticate via JWT tokens stored in localStorage
2. **Write Code**: Users write FastAPI code in a Monaco Editor (VS Code editor in browser)
3. **Deploy**: Code is validated, then deployed to Kubernetes as an isolated application
4. **Access**: Each app gets a unique URL: `platform.gofastapi.xyz/user/{user_id}/app/{app_id}`

### Deployment Process

When a user clicks "Deploy", the backend:

1. **Validates Code**: 
   - Syntax check via Python AST parsing
   - Security check: ensures `app = FastAPI()` exists
   - Import whitelist: only allows safe imports (FastAPI, Pydantic, stdlib)

2. **Creates Kubernetes Resources** (in order):
   - **ConfigMap**: Stores user code as `user_code.py`
   - **Deployment**: Runs pre-built `fastapi-platform-runner` container
     - Container mounts ConfigMap as `/app/user_code.py`
     - Runner executes user code and starts uvicorn server
   - **Service**: Exposes the pod internally on port 80
   - **Middleware**: Strips path prefix `/user/{user_id}/app/{app_id}` 
   - **IngressRoute**: Routes external traffic via Traefik

3. **Status Polling**: Frontend polls `/api/apps/{app_id}/status` to show deployment progress

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │────▶│   Frontend   │────▶│     Backend     │
│  (React)    │     │   (Nginx)    │     │    (FastAPI)    │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                    ┌─────▼─────┐          ┌──────▼──────┐         ┌─────▼─────┐
                    │  MongoDB  │          │ Kubernetes  │         │  Traefik   │
                    │  (Users,  │          │   (Pods,    │         │ (Ingress)  │
                    │   Apps)   │          │  Services)  │         │            │
                    └───────────┘          └──────┬──────┘         └─────┬──────┘
                                                    │                      │
                                          ┌─────────▼──────────┐          │
                                          │  User App Pods     │◀─────────┘
                                          │  (Runner Container)│
                                          │  - Reads code from │
                                          │    ConfigMap       │
                                          │  - Executes code   │
                                          │  - Serves FastAPI  │
                                          └────────────────────┘
```

### Components

**Frontend** (`frontend/`)
- React 18 + Vite
- Monaco Editor for code editing
- JWT-based authentication
- Real-time deployment status polling

**Backend** (`backend/`)
- FastAPI REST API
- MongoDB for user/app data
- Kubernetes Python client for dynamic resource creation
- Code validation and security checks

**Runner** (`runner/`)
- Pre-built Docker image with FastAPI + uvicorn
- Entrypoint script (`entrypoint.py`) that:
  1. Reads user code from mounted ConfigMap
  2. Executes code in isolated namespace
  3. Extracts `app = FastAPI()` instance
  4. Adds `/health` endpoint if missing
  5. Starts uvicorn server

### Security

- **Code Validation**: AST parsing blocks dangerous operations
- **Import Whitelist**: Only FastAPI ecosystem + safe stdlib
- **Resource Limits**: CPU (250m) and memory (128Mi) per pod
- **Isolation**: Each user app runs in separate pod with own ConfigMap
- **Authentication**: JWT tokens for API access

### Routing

User apps are accessible at:
```
https://platform.gofastapi.xyz/user/{user_id}/app/{app_id}/*
```

Traefik routing flow:
1. Request hits Traefik IngressRoute
2. Middleware strips `/user/{user_id}/app/{app_id}` prefix
3. Request forwarded to Service → Pod
4. User's FastAPI app handles the request

### Ephemeral Apps

- Apps auto-delete after 24 hours of inactivity
- Activity tracked via `/api/apps/{app_id}/activity` endpoint
- Cleanup job runs periodically in backend

## Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
export MONGO_URI="mongodb://localhost:27017"
export SECRET_KEY="dev-secret-key"
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Runner
```bash
cd runner
docker build -t fastapi-platform-runner:latest .
```

## Deployment

Deployed via GitOps (Flux) to Kubernetes cluster:

1. **CI/CD**: GitHub Actions workflow automatically builds and pushes images on every push to `main`
   - Images tagged with Flux-compatible format: `ts-{timestamp}-{short_sha}`
   - Pushes to GHCR: `ghcr.io/thatcatxedo/fastapi-platform-{component}`
2. **GitOps**: Flux Image Automation detects new tags and updates deployments automatically
3. **Manual**: Can also build/push manually if needed
4. Backend needs RBAC permissions to create resources in `fastapi-platform` namespace

See `homelab-cluster/apps/fastapi-platform/` for Kubernetes manifests.

## API Endpoints

- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login  
- `GET /api/auth/me` - Get current user
- `GET /api/apps` - List user's apps
- `POST /api/apps` - Create/deploy new app
- `GET /api/apps/{app_id}` - Get app details
- `PUT /api/apps/{app_id}` - Update app code (redeploy)
- `DELETE /api/apps/{app_id}` - Delete app
- `GET /api/apps/{app_id}/status` - Get deployment status
