"""
Authentication routes for FastAPI Platform.

This module contains thin HTTP handlers that delegate to UserService
for business logic.
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from models import UserSignup, UserLogin, UserResponse, TokenResponse
from auth import create_access_token, get_current_user
from utils import error_payload
from services.user_service import (
    user_service,
    UserServiceError,
    SignupsDisabledError,
    UserExistsError,
    InvalidCredentialsError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def handle_service_error(e: UserServiceError) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    status_map = {
        "SIGNUPS_DISABLED": 403,
        "USER_EXISTS": 400,
        "INVALID_CREDENTIALS": 401,
        "USER_NOT_FOUND": 404,
    }
    status_code = status_map.get(e.code, 500)

    # Use error_payload for structured errors, simple string for auth errors
    if e.code in ("SIGNUPS_DISABLED",):
        return HTTPException(
            status_code=status_code,
            detail=error_payload(e.code, e.message)
        )
    return HTTPException(
        status_code=status_code,
        detail=e.message
    )


# Re-export for backwards compatibility with admin router
def build_user_response(user: dict) -> UserResponse:
    """Build a UserResponse from a user document."""
    return user_service.to_response(user)


@router.post("/signup", response_model=UserResponse)
async def signup(user_data: UserSignup):
    """Create a new user account."""
    try:
        user = await user_service.signup(user_data)
        return user_service.to_response(user)
    except UserServiceError as e:
        raise handle_service_error(e)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Authenticate and get access token."""
    try:
        user = await user_service.validate_login(credentials.username, credentials.password)
        access_token = create_access_token(data={"sub": str(user["_id"])})
        return TokenResponse(access_token=access_token, token_type="bearer")
    except UserServiceError as e:
        raise handle_service_error(e)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information."""
    return user_service.to_response(user)
