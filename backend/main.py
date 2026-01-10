from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import List, Optional
import os
import bcrypt
import secrets
import string
from datetime import datetime, timedelta
from jose import JWTError, jwt
import ast
import re
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed templates
    from seed_templates import seed_templates
    try:
        await seed_templates()
        print("✓ Template seeding completed on startup")
    except Exception as e:
        print(f"Warning: Template seeding failed: {e}")
    
    yield
    # Shutdown (if needed)

app = FastAPI(title="FastAPI Learning Platform API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.fastapi_platform_db
users_collection = db.users
apps_collection = db.apps
templates_collection = db.templates

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

# Kubernetes client setup
try:
    from kubernetes import client as k8s_client, config as k8s_config
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()
    k8s_apps_v1 = k8s_client.AppsV1Api()
    k8s_core_v1 = k8s_client.CoreV1Api()
    k8s_networking_v1 = k8s_client.NetworkingV1Api()
    k8s_custom_objects = k8s_client.CustomObjectsApi()
except Exception as e:
    print(f"Warning: Kubernetes client not available: {e}")
    k8s_apps_v1 = None
    k8s_core_v1 = None
    k8s_networking_v1 = None
    k8s_custom_objects = None

# Platform settings
PLATFORM_NAMESPACE = os.getenv("PLATFORM_NAMESPACE", "fastapi-platform")
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "ghcr.io/thatcatxedo/fastapi-platform-runner:latest")
INACTIVITY_THRESHOLD_HOURS = int(os.getenv("INACTIVITY_THRESHOLD_HOURS", "24"))

# Models
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class AppCreate(BaseModel):
    name: str
    code: str

class AppUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class AppResponse(BaseModel):
    id: str
    app_id: str
    name: str
    status: str
    created_at: str
    last_activity: Optional[str]
    deployment_url: str
    error_message: Optional[str] = None

class AppDetailResponse(AppResponse):
    code: str

class AppStatusResponse(BaseModel):
    status: str
    pod_status: Optional[str] = None
    error_message: Optional[str] = None
    deployment_ready: bool = False

class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    code: str
    complexity: str
    is_global: bool
    created_at: str

# Auth utilities
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
    return user

# Code validation
ALLOWED_IMPORTS = {
    'fastapi', 'pydantic', 'typing', 'datetime', 'json', 'math', 
    'random', 'string', 'collections', 'itertools', 'functools',
    'operator', 're', 'uuid', 'hashlib', 'base64', 'urllib.parse'
}

FORBIDDEN_PATTERNS = [
    r'__import__',
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
    r'open\s*\(',
    r'file\s*\(',
    r'input\s*\(',
    r'raw_input\s*\(',
    r'subprocess',
    r'os\.system',
    r'os\.popen',
    r'socket',
    r'urllib\.request',
    r'urllib2',
]

def validate_code(code: str) -> tuple[bool, Optional[str]]:
    """Validate user code for syntax and security"""
    # Basic syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e.msg} at line {e.lineno}"
    
    # Check that FastAPI app is created
    has_fastapi_app = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'app':
                    if isinstance(node.value, ast.Call):
                        if isinstance(node.value.func, ast.Name) and node.value.func.id == 'FastAPI':
                            has_fastapi_app = True
                            break
    
    if not has_fastapi_app:
        return False, "Code must create a FastAPI app instance (e.g., app = FastAPI())"
    
    # Security checks - check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in ALLOWED_IMPORTS:
                    return False, f"Import '{module_name}' is not allowed. Allowed imports: {', '.join(sorted(ALLOWED_IMPORTS))}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in ALLOWED_IMPORTS:
                    return False, f"Import '{module_name}' is not allowed. Allowed imports: {', '.join(sorted(ALLOWED_IMPORTS))}"
    
    # Check for forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Forbidden pattern detected: {pattern}"
    
    return True, None

# Routes
@app.get("/")
async def root():
    return {"message": "FastAPI Learning Platform API", "version": "1.0.0"}

@app.get("/health")
async def health():
    try:
        await client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(user_data: UserSignup):
    # Check if username or email already exists
    existing = await users_collection.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create user
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.utcnow()
    }
    result = await users_collection.insert_one(user_doc)
    
    user = await users_collection.find_one({"_id": result.inserted_id})
    return UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"].isoformat()
    )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await users_collection.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return TokenResponse(access_token=access_token, token_type="bearer")

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"].isoformat()
    )

from deployment import create_app_deployment, delete_app_deployment, update_app_deployment, get_deployment_status
import logging

logger = logging.getLogger(__name__)

@app.get("/api/apps", response_model=List[AppResponse])
async def list_apps(user: dict = Depends(get_current_user)):
    apps = []
    async for app in apps_collection.find({"user_id": user["_id"], "status": {"$ne": "deleted"}}):
        apps.append(AppResponse(
            id=str(app["_id"]),
            app_id=app["app_id"],
            name=app["name"],
            status=app["status"],
            created_at=app["created_at"].isoformat(),
            last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
            deployment_url=app["deployment_url"],
            error_message=app.get("error_message")
        ))
    return apps

@app.post("/api/apps", response_model=AppResponse)
async def create_app(app_data: AppCreate, user: dict = Depends(get_current_user)):
    # Validate code
    is_valid, error_msg = validate_code(app_data.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Code validation failed: {error_msg}")
    
    # Generate unique app_id (lowercase alphanumeric only for Kubernetes compliance)
    app_id = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    
    # Create app document
    app_doc = {
        "user_id": user["_id"],
        "app_id": app_id,
        "name": app_data.name,
        "code": app_data.code,
        "status": "deploying",
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "deployment_url": f"/user/{str(user['_id'])}/app/{app_id}"
    }
    
    result = await apps_collection.insert_one(app_doc)
    app_doc["_id"] = result.inserted_id
    
    # Deploy to Kubernetes
    try:
        await create_app_deployment(app_doc, user)
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "running"}}
        )
    except Exception as e:
        error_msg = str(e)
        # Parse Kubernetes API errors for user-friendly messages
        if "Invalid value" in error_msg and "metadata.name" in error_msg:
            error_msg = "Invalid app name. Please use only lowercase letters, numbers, and hyphens."
        elif "already exists" in error_msg.lower():
            error_msg = "An app with this name already exists. Please try again."
        elif "Forbidden" in error_msg or "403" in error_msg:
            error_msg = "Permission denied. Please contact support."
        elif "not found" in error_msg.lower():
            error_msg = "Resource not found. Please try again."
        else:
            # Extract the main error message if it's a Kubernetes error
            if "message" in error_msg:
                import json
                try:
                    error_dict = json.loads(error_msg.split("HTTP response body:")[-1].strip())
                    if "message" in error_dict:
                        error_msg = error_dict["message"]
                except:
                    pass
        
        await apps_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "error", "error_message": error_msg}}
        )
        raise HTTPException(status_code=500, detail=error_msg)
    
    updated_app = await apps_collection.find_one({"_id": result.inserted_id})
    return AppResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message")
    )

@app.get("/api/apps/{app_id}", response_model=AppDetailResponse)
async def get_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return AppDetailResponse(
        id=str(app["_id"]),
        app_id=app["app_id"],
        name=app["name"],
        code=app["code"],
        status=app["status"],
        created_at=app["created_at"].isoformat(),
        last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
        deployment_url=app["deployment_url"],
        error_message=app.get("error_message")
    )

@app.put("/api/apps/{app_id}", response_model=AppResponse)
async def update_app(app_id: str, app_data: AppUpdate, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    update_data = {}
    if app_data.name is not None:
        update_data["name"] = app_data.name
    if app_data.code is not None:
        # Validate code
        is_valid, error_msg = validate_code(app_data.code)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Code validation failed: {error_msg}")
        update_data["code"] = app_data.code
        update_data["status"] = "deploying"
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": update_data}
    )
    
    # Update deployment if code changed
    if app_data.code is not None:
        updated_app = await apps_collection.find_one({"_id": app["_id"]})
        try:
            await update_app_deployment(updated_app, user)
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": "running"}}
            )
        except Exception as e:
            error_msg = str(e)
            # Parse Kubernetes API errors for user-friendly messages
            if "Invalid value" in error_msg and "metadata.name" in error_msg:
                error_msg = "Invalid app name. Please use only lowercase letters, numbers, and hyphens."
            elif "already exists" in error_msg.lower():
                error_msg = "An app with this name already exists. Please try again."
            elif "Forbidden" in error_msg or "403" in error_msg:
                error_msg = "Permission denied. Please contact support."
            elif "not found" in error_msg.lower():
                error_msg = "Resource not found. Please try again."
            else:
                import json
                try:
                    error_dict = json.loads(error_msg.split("HTTP response body:")[-1].strip())
                    if "message" in error_dict:
                        error_msg = error_dict["message"]
                except:
                    pass
            
            await apps_collection.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": "error", "error_message": error_msg}}
            )
            raise HTTPException(status_code=500, detail=error_msg)
    
    updated_app = await apps_collection.find_one({"_id": app["_id"]})
    return AppResponse(
        id=str(updated_app["_id"]),
        app_id=updated_app["app_id"],
        name=updated_app["name"],
        status=updated_app["status"],
        created_at=updated_app["created_at"].isoformat(),
        last_activity=updated_app.get("last_activity").isoformat() if updated_app.get("last_activity") else None,
        deployment_url=updated_app["deployment_url"],
        error_message=updated_app.get("error_message")
    )

@app.delete("/api/apps/{app_id}")
async def delete_app(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Delete from Kubernetes
    try:
        await delete_app_deployment(app, user)
    except Exception as e:
        print(f"Error deleting deployment: {e}")
    
    # Mark as deleted in database
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {"status": "deleted"}}
    )
    
    return {"success": True, "message": "App deleted"}

@app.get("/api/apps/{app_id}/status", response_model=AppStatusResponse)
async def get_app_status(app_id: str, user: dict = Depends(get_current_user)):
    """Get deployment status for an app"""
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    pod_status = None
    deployment_ready = False
    
    # Check Kubernetes deployment status if available
    try:
        k8s_status = await get_deployment_status(app, user)
        if k8s_status:
            pod_status = k8s_status.get("pod_status")
            deployment_ready = k8s_status.get("ready", False)
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")
    
    return AppStatusResponse(
        status=app["status"],
        pod_status=pod_status,
        error_message=app.get("error_message"),
        deployment_ready=deployment_ready
    )

@app.post("/api/apps/{app_id}/activity")
async def record_activity(app_id: str, user: dict = Depends(get_current_user)):
    app = await apps_collection.find_one({"app_id": app_id, "user_id": user["_id"]})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    await apps_collection.update_one(
        {"_id": app["_id"]},
        {"$set": {"last_activity": datetime.utcnow()}}
    )
    
    return {"success": True}

@app.get("/api/templates", response_model=List[TemplateResponse])
async def list_templates(user: dict = Depends(get_current_user)):
    """List all templates (global + user's templates)"""
    # Get global templates
    global_templates = await templates_collection.find({"is_global": True}).to_list(length=100)
    
    # Get user's templates
    user_templates = await templates_collection.find({
        "is_global": False,
        "user_id": user["_id"]
    }).to_list(length=100)
    
    # Combine and convert to response
    all_templates = global_templates + user_templates
    return [
        TemplateResponse(
            id=str(t["_id"]),
            name=t["name"],
            description=t["description"],
            code=t["code"],
            complexity=t["complexity"],
            is_global=t["is_global"],
            created_at=t["created_at"].isoformat() if isinstance(t.get("created_at"), datetime) else t.get("created_at", "")
        )
        for t in all_templates
    ]

@app.get("/api/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    """Get a specific template"""
    try:
        template = await templates_collection.find_one({"_id": ObjectId(template_id)})
    except:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if user can access this template (global or user's own)
    if not template.get("is_global") and str(template.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TemplateResponse(
        id=str(template["_id"]),
        name=template["name"],
        description=template["description"],
        code=template["code"],
        complexity=template["complexity"],
        is_global=template["is_global"],
        created_at=template["created_at"].isoformat() if isinstance(template.get("created_at"), datetime) else template.get("created_at", "")
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
