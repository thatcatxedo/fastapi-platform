"""
User service for FastAPI Platform.

This service handles user CRUD operations including signup, login validation,
and MongoDB user provisioning.
"""
import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from models import UserSignup, UserResponse

logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Base exception for user service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SignupsDisabledError(UserServiceError):
    """Raised when signups are disabled."""
    def __init__(self):
        super().__init__("SIGNUPS_DISABLED", "Public signups are disabled")


class UserExistsError(UserServiceError):
    """Raised when username or email already exists."""
    def __init__(self):
        super().__init__("USER_EXISTS", "Username or email already exists")


class InvalidCredentialsError(UserServiceError):
    """Raised when login credentials are invalid."""
    def __init__(self):
        super().__init__("INVALID_CREDENTIALS", "Invalid username or password")


class UserNotFoundError(UserServiceError):
    """Raised when a user is not found."""
    def __init__(self, user_id: str):
        super().__init__("USER_NOT_FOUND", f"User not found: {user_id}")


class UserService:
    """Service for user CRUD operations and authentication."""

    def __init__(
        self,
        users_collection=None,
        settings_collection=None,
        mongo_client=None
    ):
        """
        Initialize UserService with optional dependency injection.
        """
        if users_collection is None:
            from database import (
                users_collection as default_users,
                settings_collection as default_settings,
                client as default_client
            )
            self.users = default_users
            self.settings = default_settings
            self.client = default_client
        else:
            self.users = users_collection
            self.settings = settings_collection
            self.client = mongo_client

    # =========================================================================
    # Response Builder
    # =========================================================================

    @staticmethod
    def to_response(user: dict) -> UserResponse:
        """
        Build a UserResponse from a user document.

        Args:
            user: User document from MongoDB

        Returns:
            UserResponse model instance
        """
        return UserResponse(
            id=str(user["_id"]),
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"].isoformat(),
            is_admin=user.get("is_admin", False)
        )

    # =========================================================================
    # Signup
    # =========================================================================

    async def signup(self, user_data: UserSignup) -> dict:
        """
        Create a new user account with MongoDB user provisioning.

        Args:
            user_data: User signup data

        Returns:
            Created user document

        Raises:
            SignupsDisabledError: If public signups are disabled
            UserExistsError: If username or email already exists
        """
        from auth import hash_password
        from mongo_users import (
            create_mongo_user_for_database, create_viewer_user, encrypt_password
        )

        # Check if signups are allowed
        settings = await self.settings.find_one({"_id": "global"})
        if settings and not settings.get("allow_signups", True):
            raise SignupsDisabledError()

        # Check if username or email already exists
        existing = await self.users.find_one({
            "$or": [
                {"username": user_data.username},
                {"email": user_data.email}
            ]
        })
        if existing:
            raise UserExistsError()

        # Check if this is the first user (becomes admin)
        user_count = await self.users.count_documents({})
        is_first_user = user_count == 0

        # Create user document
        now = datetime.utcnow()
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "created_at": now,
            "is_admin": is_first_user,  # First user is admin
            # Multi-database support
            "databases": [],  # Will be populated after MongoDB user creation
            "default_database_id": "default"
        }
        result = await self.users.insert_one(user_doc)

        # Initialize settings on first signup
        if is_first_user:
            await self.settings.update_one(
                {"_id": "global"},
                {"$setOnInsert": {
                    "allow_signups": True,
                    "updated_at": now
                }},
                upsert=True
            )

        # Create per-user MongoDB credentials for default database
        user_id = str(result.inserted_id)
        await self._provision_mongo_user(user_id, result.inserted_id, now)

        return await self.users.find_one({"_id": result.inserted_id})

    async def _provision_mongo_user(
        self,
        user_id: str,
        inserted_id: ObjectId,
        created_at: datetime
    ) -> None:
        """
        Provision MongoDB user and viewer for a new platform user.

        Args:
            user_id: String user ID
            inserted_id: ObjectId of inserted user
            created_at: Creation timestamp
        """
        from mongo_users import (
            create_mongo_user_for_database, create_viewer_user, encrypt_password
        )

        try:
            mongo_username, mongo_password = await create_mongo_user_for_database(
                self.client, user_id, "default"
            )

            # Create viewer user with access to all databases (just default for now)
            viewer_password = await create_viewer_user(self.client, user_id, ["default"])

            # Create default database entry
            default_db_entry = {
                "id": "default",
                "name": "Default",
                "mongo_password_encrypted": encrypt_password(mongo_password),
                "created_at": created_at,
                "is_default": True,
                "description": "Default database"
            }

            # Store database entry and viewer password in user document
            await self.users.update_one(
                {"_id": inserted_id},
                {"$set": {
                    "databases": [default_db_entry],
                    "viewer_password_encrypted": encrypt_password(viewer_password)
                }}
            )
            logger.info(f"Created MongoDB user {mongo_username} and viewer for platform user {user_id}")
        except Exception as e:
            # Log error but don't fail signup - user can still use platform without MongoDB access
            logger.error(f"Failed to create MongoDB user for {user_id}: {e}")

    # =========================================================================
    # Login Validation
    # =========================================================================

    async def validate_login(self, username: str, password: str) -> dict:
        """
        Validate login credentials and return user if valid.

        Args:
            username: Username to validate
            password: Password to validate

        Returns:
            User document if credentials are valid

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        from auth import verify_password

        user = await self.users.find_one({"username": username})
        if not user or not verify_password(password, user["password_hash"]):
            raise InvalidCredentialsError()

        return user

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_by_id(self, user_id: str) -> dict:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User document

        Raises:
            UserNotFoundError: If user not found
        """
        try:
            user = await self.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise UserNotFoundError(user_id)

        if not user:
            raise UserNotFoundError(user_id)

        return user


# Singleton instance for production use
user_service = UserService()
