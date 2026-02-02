"""
Admin service for FastAPI Platform.

This service handles administrative operations including settings management,
user management, platform statistics, and cascade user deletion.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bson import ObjectId

from models import AdminSettingsUpdate, AdminStatusUpdate, UserSignup

logger = logging.getLogger(__name__)


class AdminServiceError(Exception):
    """Base exception for admin service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class UserNotFoundError(AdminServiceError):
    """Raised when a user is not found."""
    def __init__(self, user_id: str):
        super().__init__("USER_NOT_FOUND", f"User not found: {user_id}")


class CannotDemoteSelfError(AdminServiceError):
    """Raised when admin tries to demote themselves."""
    def __init__(self):
        super().__init__("CANNOT_DEMOTE_SELF", "Cannot remove your own admin status")


class CannotRemoveLastAdminError(AdminServiceError):
    """Raised when trying to remove the last admin."""
    def __init__(self):
        super().__init__("CANNOT_REMOVE_LAST_ADMIN", "Cannot remove the last admin")


class CannotDeleteSelfError(AdminServiceError):
    """Raised when admin tries to delete themselves."""
    def __init__(self):
        super().__init__("CANNOT_DELETE_SELF", "Cannot delete your own account")


class InvalidSettingsError(AdminServiceError):
    """Raised when settings are invalid."""
    def __init__(self, reason: str):
        super().__init__("INVALID_SETTINGS", reason)


class UserExistsError(AdminServiceError):
    """Raised when user already exists."""
    def __init__(self):
        super().__init__("USER_EXISTS", "Username or email already exists")


class AdminService:
    """Service for administrative operations."""

    def __init__(
        self,
        users_collection=None,
        apps_collection=None,
        templates_collection=None,
        settings_collection=None,
        viewer_instances_collection=None,
        mongo_client=None
    ):
        """
        Initialize AdminService with optional dependency injection.
        """
        if users_collection is None:
            from database import (
                users_collection as default_users,
                apps_collection as default_apps,
                templates_collection as default_templates,
                settings_collection as default_settings,
                viewer_instances_collection as default_viewers,
                client as default_client
            )
            self.users = default_users
            self.apps = default_apps
            self.templates = default_templates
            self.settings = default_settings
            self.viewers = default_viewers
            self.client = default_client
        else:
            self.users = users_collection
            self.apps = apps_collection
            self.templates = templates_collection
            self.settings = settings_collection
            self.viewers = viewer_instances_collection
            self.client = mongo_client

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def normalize_allowed_imports(allowed_imports: List[str]) -> List[str]:
        """
        Normalize and deduplicate allowed imports list.

        Args:
            allowed_imports: Raw list of import names

        Returns:
            Sorted, deduplicated, lowercase list of imports
        """
        normalized = [
            item.strip().lower()
            for item in allowed_imports
            if isinstance(item, str)
        ]
        normalized = [item for item in normalized if item]
        return sorted(set(normalized))

    # =========================================================================
    # Settings Management
    # =========================================================================

    async def get_settings(self) -> dict:
        """
        Get platform settings.

        Returns:
            Dict with allow_signups and allowed_imports
        """
        from validation import ALLOWED_IMPORTS

        settings = await self.settings.find_one({"_id": "global"})
        allowed_imports = settings.get("allowed_imports") if settings else None

        if not allowed_imports:
            allowed_imports = sorted(ALLOWED_IMPORTS)
        else:
            allowed_imports = self.normalize_allowed_imports(allowed_imports)

        return {
            "allow_signups": settings.get("allow_signups", True) if settings else True,
            "allowed_imports": allowed_imports
        }

    async def update_settings(self, settings_data: AdminSettingsUpdate, admin: dict) -> bool:
        """
        Update platform settings.

        Args:
            settings_data: New settings values
            admin: Admin user making the change

        Returns:
            True if successful

        Raises:
            InvalidSettingsError: If settings are invalid
        """
        allowed_imports = self.normalize_allowed_imports(settings_data.allowed_imports)

        if not allowed_imports:
            raise InvalidSettingsError("allowed_imports must include at least one module")

        await self.settings.update_one(
            {"_id": "global"},
            {"$set": {
                "allow_signups": settings_data.allow_signups,
                "allowed_imports": allowed_imports,
                "updated_at": datetime.utcnow(),
                "updated_by": admin["_id"]
            }},
            upsert=True
        )

        return True

    # =========================================================================
    # User Management
    # =========================================================================

    async def list_users_with_stats(self) -> List[dict]:
        """
        List all users with their app counts.

        Returns:
            List of user dicts with app statistics
        """
        users = []
        async for user in self.users.find().sort("created_at", -1):
            app_count = await self.apps.count_documents({"user_id": user["_id"]})
            running_app_count = await self.apps.count_documents({
                "user_id": user["_id"],
                "status": "running"
            })
            users.append({
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "created_at": user["created_at"].isoformat(),
                "is_admin": user.get("is_admin", False),
                "app_count": app_count,
                "running_app_count": running_app_count
            })
        return users

    async def update_admin_status(
        self,
        user_id: str,
        status_update: AdminStatusUpdate,
        admin: dict
    ) -> dict:
        """
        Promote or demote a user to/from admin status.

        Args:
            user_id: Target user ID
            status_update: New admin status
            admin: Admin making the change

        Returns:
            Dict with success status and new is_admin value

        Raises:
            CannotDemoteSelfError: If admin tries to demote themselves
            UserNotFoundError: If user doesn't exist
            CannotRemoveLastAdminError: If this would remove last admin
        """
        # Prevent self-demotion
        if str(admin["_id"]) == user_id and not status_update.is_admin:
            raise CannotDemoteSelfError()

        # Check if user exists
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise UserNotFoundError(user_id)

        # Prevent removing the last admin
        if not status_update.is_admin:
            admin_count = await self.users.count_documents({"is_admin": True})
            if admin_count <= 1:
                raise CannotRemoveLastAdminError()

        # Update user's admin status
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_admin": status_update.is_admin}}
        )

        action = "promoted to" if status_update.is_admin else "demoted from"
        logger.info(f"User {user['username']} {action} admin by {admin['username']}")

        return {"success": True, "is_admin": status_update.is_admin}

    async def create_user(self, user_data: UserSignup, admin: dict) -> dict:
        """
        Create a new user (admin action, bypasses signup restrictions).

        Args:
            user_data: User signup data
            admin: Admin creating the user

        Returns:
            Created user document

        Raises:
            UserExistsError: If username or email already exists
        """
        from auth import hash_password
        from mongo_users import create_mongo_user, encrypt_password

        # Check for existing user
        existing = await self.users.find_one({
            "$or": [
                {"username": user_data.username},
                {"email": user_data.email}
            ]
        })
        if existing:
            raise UserExistsError()

        # Create user document
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "created_at": datetime.utcnow(),
            "is_admin": False
        }
        result = await self.users.insert_one(user_doc)

        # Create MongoDB user
        try:
            mongo_username, mongo_password = await create_mongo_user(
                self.client, str(result.inserted_id)
            )
            await self.users.update_one(
                {"_id": result.inserted_id},
                {"$set": {"mongo_password_encrypted": encrypt_password(mongo_password)}}
            )
        except Exception as e:
            logger.error(f"Failed to create MongoDB user: {e}")

        return await self.users.find_one({"_id": result.inserted_id})

    async def delete_user(self, user_id: str, admin: dict) -> dict:
        """
        Delete a user with full cascade cleanup.

        Deletes: user's apps (K8s + DB), MongoDB user, user database, viewer, user record.

        Args:
            user_id: User ID to delete
            admin: Admin performing deletion

        Returns:
            Dict with success status and deleted user ID

        Raises:
            CannotDeleteSelfError: If admin tries to delete themselves
            UserNotFoundError: If user doesn't exist
        """
        from deployment import delete_app_deployment, delete_mongo_viewer_resources
        from mongo_users import delete_mongo_user

        # Prevent self-deletion
        if str(admin["_id"]) == user_id:
            raise CannotDeleteSelfError()

        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise UserNotFoundError(user_id)

        # Delete user's apps (K8s resources + DB records)
        async for app in self.apps.find({"user_id": ObjectId(user_id)}):
            try:
                await delete_app_deployment(app, user)
            except Exception as e:
                logger.warning(f"Failed to delete app {app['app_id']}: {e}")

        await self.apps.delete_many({"user_id": ObjectId(user_id)})

        # Delete MongoDB user
        try:
            await delete_mongo_user(self.client, user_id)
        except Exception as e:
            logger.warning(f"Failed to delete MongoDB user for {user_id}: {e}")

        # Delete user's database
        try:
            await self.client.drop_database(f"user_{user_id}")
        except Exception as e:
            logger.warning(f"Failed to drop database for {user_id}: {e}")

        # Delete viewer instance and resources
        viewer = await self.viewers.find_one({"user_id": ObjectId(user_id)})
        if viewer:
            try:
                await delete_mongo_viewer_resources(user_id)
            except Exception as e:
                logger.warning(f"Failed to delete viewer resources for {user_id}: {e}")
            await self.viewers.delete_many({"user_id": ObjectId(user_id)})

        # Delete user record
        await self.users.delete_one({"_id": ObjectId(user_id)})

        return {"success": True, "deleted_user_id": user_id}

    # =========================================================================
    # Platform Statistics
    # =========================================================================

    async def get_platform_stats(self) -> dict:
        """
        Get comprehensive platform statistics.

        Returns:
            Dict with user counts, app counts, MongoDB stats, recent activity
        """
        user_count = await self.users.count_documents({})
        app_count = await self.apps.count_documents({})
        running_apps = await self.apps.count_documents({"status": "running"})
        template_count = await self.templates.count_documents({})

        recent_users = await self.users.find().sort("created_at", -1).limit(5).to_list(5)
        recent_apps = await self.apps.find().sort("created_at", -1).limit(5).to_list(5)

        # MongoDB stats
        mongo_stats = await self._get_mongo_stats()

        return {
            "users": user_count,
            "apps": app_count,
            "running_apps": running_apps,
            "templates": template_count,
            "mongo": mongo_stats,
            "recent_signups": [
                {"username": u["username"], "created_at": u["created_at"].isoformat()}
                for u in recent_users
            ],
            "recent_deploys": [
                {"name": a["name"], "app_id": a["app_id"], "created_at": a["created_at"].isoformat()}
                for a in recent_apps
            ]
        }

    async def _get_mongo_stats(self) -> dict:
        """
        Get MongoDB storage statistics.

        Returns:
            Dict with database counts and storage sizes
        """
        try:
            db_list = await self.client.list_database_names()
            user_dbs = [db for db in db_list if db.startswith("user_")]

            total_storage = 0
            total_collections = 0
            total_documents = 0

            for db_name in user_dbs:
                try:
                    db = self.client[db_name]
                    stats = await db.command("dbStats")
                    total_storage += stats.get("storageSize", 0)
                    total_collections += stats.get("collections", 0)
                    total_documents += stats.get("objects", 0)
                except Exception:
                    pass

            # Platform DB stats
            platform_db = self.client.fastapi_platform_db
            platform_stats = await platform_db.command("dbStats")

            return {
                "user_databases": len(user_dbs),
                "total_storage_mb": round(total_storage / (1024 * 1024), 2),
                "total_collections": total_collections,
                "total_documents": total_documents,
                "platform_storage_mb": round(platform_stats.get("storageSize", 0) / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.warning(f"Failed to get MongoDB stats: {e}")
            return {"error": str(e)}


# Singleton instance for production use
admin_service = AdminService()
