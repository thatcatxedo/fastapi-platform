"""
Authentication routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from models import UserSignup, UserLogin, UserResponse, TokenResponse
from auth import hash_password, verify_password, create_access_token, get_current_user
from database import users_collection, settings_collection, client
from utils import error_payload
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def build_user_response(user: dict) -> UserResponse:
    """Build a UserResponse from a user document."""
    return UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"].isoformat(),
        is_admin=user.get("is_admin", False)
    )


@router.post("/signup", response_model=UserResponse)
async def signup(user_data: UserSignup):
    # Check if signups are allowed
    settings = await settings_collection.find_one({"_id": "global"})
    if settings and not settings.get("allow_signups", True):
        raise HTTPException(
            status_code=403,
            detail=error_payload("SIGNUPS_DISABLED", "Public signups are disabled")
        )
    
    # Check if username or email already exists
    existing = await users_collection.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Check if this is the first user (becomes admin)
    user_count = await users_collection.count_documents({})
    is_first_user = user_count == 0
    
    # Create user
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.utcnow(),
        "is_admin": is_first_user  # First user is admin
    }
    result = await users_collection.insert_one(user_doc)
    
    # Initialize settings on first signup
    if is_first_user:
        await settings_collection.update_one(
            {"_id": "global"},
            {"$setOnInsert": {
                "allow_signups": True,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
    
    # Create per-user MongoDB credentials for data isolation
    try:
        from mongo_users import create_mongo_user, encrypt_password
        mongo_username, mongo_password = await create_mongo_user(client, str(result.inserted_id))
        
        # Store encrypted MongoDB password in user document
        await users_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"mongo_password_encrypted": encrypt_password(mongo_password)}}
        )
        logger.info(f"Created MongoDB user {mongo_username} for platform user {result.inserted_id}")
    except Exception as e:
        # Log error but don't fail signup - user can still use platform without MongoDB access
        logger.error(f"Failed to create MongoDB user for {result.inserted_id}: {e}")
    
    user = await users_collection.find_one({"_id": result.inserted_id})
    return build_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await users_collection.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    return build_user_response(user)
