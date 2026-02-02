"""
Database management service for FastAPI Platform.

This service handles multi-database operations including CRUD,
MongoDB user management, stats collection, and viewer deployment.
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from models import DatabaseCreate, DatabaseUpdate, DatabaseResponse, DatabaseListResponse, ViewerResponse

logger = logging.getLogger(__name__)

MAX_DATABASES_PER_USER = 10


class DatabaseServiceError(Exception):
    """Base exception for database service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class DatabaseNotFoundError(DatabaseServiceError):
    """Raised when a database is not found."""
    def __init__(self, database_id: str):
        super().__init__("NOT_FOUND", f"Database not found: {database_id}")


class DatabaseLimitReachedError(DatabaseServiceError):
    """Raised when user has reached database limit."""
    def __init__(self):
        super().__init__(
            "LIMIT_REACHED",
            f"Maximum {MAX_DATABASES_PER_USER} databases allowed"
        )


class DuplicateNameError(DatabaseServiceError):
    """Raised when database name already exists."""
    def __init__(self, name: str):
        super().__init__(
            "DUPLICATE_NAME",
            f"A database with this name already exists: {name}"
        )


class CannotDeleteError(DatabaseServiceError):
    """Raised when database cannot be deleted."""
    def __init__(self, reason: str):
        super().__init__("CANNOT_DELETE", reason)


class DatabaseInUseError(DatabaseServiceError):
    """Raised when database is still in use by apps."""
    def __init__(self, app_count: int):
        super().__init__(
            "DATABASE_IN_USE",
            f"{app_count} app(s) are using this database. Update them to use a different database first."
        )


class DatabaseCreateError(DatabaseServiceError):
    """Raised when database creation fails."""
    def __init__(self, reason: str = "Failed to create database"):
        super().__init__("DB_CREATE_FAILED", reason)


class ViewerLaunchError(DatabaseServiceError):
    """Raised when viewer launch fails."""
    def __init__(self, reason: str):
        super().__init__("VIEWER_LAUNCH_FAILED", reason)


class NoDatabasesError(DatabaseServiceError):
    """Raised when user has no databases."""
    def __init__(self):
        super().__init__("NO_DATABASES", "No databases found for this user")


class DatabaseService:
    """Service for database CRUD operations and viewer management."""

    def __init__(
        self,
        users_collection=None,
        apps_collection=None,
        mongo_client=None,
        app_domain: str = None
    ):
        """
        Initialize DatabaseService with optional dependency injection.

        Args:
            users_collection: MongoDB collection for users (uses default if None)
            apps_collection: MongoDB collection for apps (uses default if None)
            mongo_client: MongoDB client for database operations (uses default if None)
            app_domain: Domain for viewer URLs (uses config default if None)
        """
        if users_collection is None:
            from database import users_collection as default_users
            from database import apps_collection as default_apps
            from database import client as default_client
            self.users = default_users
            self.apps = default_apps
            self.client = default_client
        else:
            self.users = users_collection
            self.apps = apps_collection
            self.client = mongo_client

        if app_domain is None:
            from config import APP_DOMAIN
            self.app_domain = APP_DOMAIN
        else:
            self.app_domain = app_domain

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def format_datetime(dt) -> str:
        """Format datetime to ISO string."""
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)

    @staticmethod
    def generate_database_id() -> str:
        """Generate a unique database ID."""
        return str(uuid.uuid4())[:8]

    def get_mongo_db_name(self, user_id: str, database_id: str) -> str:
        """Get the MongoDB database name for a user's database."""
        from mongo_users import get_mongo_db_name
        return get_mongo_db_name(user_id, database_id)

    async def get_database_stats(self, user_id: str, database_id: str) -> dict:
        """
        Get stats for a specific user database.

        Args:
            user_id: User identifier
            database_id: Database identifier

        Returns:
            Dict with collection count, document count, and size
        """
        db_name = self.get_mongo_db_name(user_id, database_id)
        user_db = self.client[db_name]

        try:
            collection_names = await user_db.list_collection_names()
            db_stats = await user_db.command("dbStats")

            return {
                "total_collections": len(collection_names),
                "total_documents": db_stats.get("objects", 0),
                "total_size_bytes": db_stats.get("dataSize", 0),
                "total_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.warning(f"Error getting stats for {db_name}: {e}")
            return {
                "total_collections": 0,
                "total_documents": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0
            }

    # =========================================================================
    # Response Builders
    # =========================================================================

    def to_response(self, db_entry: dict, user_id: str, stats: dict = None) -> DatabaseResponse:
        """
        Build a DatabaseResponse from a database entry.

        Args:
            db_entry: Database entry from user document
            user_id: User identifier
            stats: Optional pre-computed stats

        Returns:
            DatabaseResponse model instance
        """
        if stats is None:
            stats = {
                "total_collections": 0,
                "total_documents": 0,
                "total_size_mb": 0
            }

        return DatabaseResponse(
            id=db_entry["id"],
            name=db_entry["name"],
            description=db_entry.get("description"),
            is_default=db_entry.get("is_default", False),
            mongo_database=self.get_mongo_db_name(user_id, db_entry["id"]),
            created_at=self.format_datetime(db_entry["created_at"]),
            total_collections=stats["total_collections"],
            total_documents=stats["total_documents"],
            total_size_mb=stats["total_size_mb"]
        )

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_database_entry(self, databases: List[dict], database_id: str) -> dict:
        """
        Get a database entry by ID from user's databases list.

        Args:
            databases: List of database entries from user document
            database_id: Database identifier

        Returns:
            Database entry dict

        Raises:
            DatabaseNotFoundError: If database not found
        """
        db_entry = next((db for db in databases if db["id"] == database_id), None)
        if not db_entry:
            raise DatabaseNotFoundError(database_id)
        return db_entry

    def get_database_index(self, databases: List[dict], database_id: str) -> int:
        """
        Get the index of a database entry in user's databases list.

        Args:
            databases: List of database entries from user document
            database_id: Database identifier

        Returns:
            Index of database entry

        Raises:
            DatabaseNotFoundError: If database not found
        """
        db_index = next((i for i, db in enumerate(databases) if db["id"] == database_id), None)
        if db_index is None:
            raise DatabaseNotFoundError(database_id)
        return db_index

    async def list_for_user(self, user: dict) -> Tuple[List[DatabaseResponse], float, str]:
        """
        List all databases for a user with stats.

        Args:
            user: User document

        Returns:
            Tuple of (list of DatabaseResponse, total_size_mb, default_database_id)
        """
        user_id = str(user["_id"])
        databases = user.get("databases", [])

        result = []
        total_size = 0

        for db_entry in databases:
            stats = await self.get_database_stats(user_id, db_entry["id"])
            total_size += stats["total_size_mb"]
            result.append(self.to_response(db_entry, user_id, stats))

        default_db_id = user.get("default_database_id", "default")
        return result, round(total_size, 2), default_db_id

    async def get_by_id(self, database_id: str, user: dict) -> Tuple[dict, dict]:
        """
        Get a database by ID with stats.

        Args:
            database_id: Database identifier
            user: User document

        Returns:
            Tuple of (database entry, stats dict)

        Raises:
            DatabaseNotFoundError: If database not found
        """
        user_id = str(user["_id"])
        databases = user.get("databases", [])

        db_entry = self.get_database_entry(databases, database_id)
        stats = await self.get_database_stats(user_id, database_id)

        return db_entry, stats

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create(self, data: DatabaseCreate, user: dict) -> DatabaseResponse:
        """
        Create a new database for a user.

        Args:
            data: Database creation data
            user: User document

        Returns:
            DatabaseResponse for the created database

        Raises:
            DatabaseLimitReachedError: If user at database limit
            DuplicateNameError: If name already exists
            DatabaseCreateError: If MongoDB user creation fails
        """
        from mongo_users import (
            create_mongo_user_for_database,
            update_viewer_user_roles,
            encrypt_password
        )

        user_id = str(user["_id"])
        databases = user.get("databases", [])

        # Check limit
        if len(databases) >= MAX_DATABASES_PER_USER:
            raise DatabaseLimitReachedError()

        # Check for duplicate name
        if any(db["name"].lower() == data.name.lower() for db in databases):
            raise DuplicateNameError(data.name)

        # Generate unique ID
        database_id = self.generate_database_id()

        # Create MongoDB user for this database
        try:
            _, mongo_password = await create_mongo_user_for_database(
                self.client, user_id, database_id
            )
        except Exception as e:
            logger.error(f"Failed to create MongoDB user: {e}")
            raise DatabaseCreateError(str(e))

        # Create database entry
        is_first_database = len(databases) == 0
        now = datetime.utcnow()
        new_db = {
            "id": database_id,
            "name": data.name,
            "description": data.description,
            "mongo_password_encrypted": encrypt_password(mongo_password),
            "created_at": now,
            "is_default": is_first_database
        }

        # Add to user's databases
        update_ops = {"$push": {"databases": new_db}}
        if is_first_database:
            update_ops["$set"] = {"default_database_id": database_id}

        await self.users.update_one({"_id": user["_id"]}, update_ops)

        # Update viewer user to include new database
        try:
            all_db_ids = [db["id"] for db in databases] + [database_id]
            await update_viewer_user_roles(self.client, user_id, all_db_ids)
        except Exception as e:
            logger.warning(f"Failed to update viewer user roles: {e}")

        return DatabaseResponse(
            id=database_id,
            name=data.name,
            description=data.description,
            is_default=is_first_database,
            mongo_database=self.get_mongo_db_name(user_id, database_id),
            created_at=self.format_datetime(now),
            total_collections=0,
            total_documents=0,
            total_size_mb=0
        )

    async def update(self, database_id: str, data: DatabaseUpdate, user: dict) -> DatabaseResponse:
        """
        Update a database's name, description, or default status.

        Args:
            database_id: Database identifier
            data: Update data
            user: User document

        Returns:
            Updated DatabaseResponse

        Raises:
            DatabaseNotFoundError: If database not found
            DuplicateNameError: If new name already exists
        """
        user_id = str(user["_id"])
        databases = user.get("databases", [])

        db_index = self.get_database_index(databases, database_id)

        update_ops = {}

        if data.name is not None:
            # Check for duplicate name
            if any(db["name"].lower() == data.name.lower() and db["id"] != database_id for db in databases):
                raise DuplicateNameError(data.name)
            update_ops[f"databases.{db_index}.name"] = data.name

        if data.description is not None:
            update_ops[f"databases.{db_index}.description"] = data.description

        if data.is_default is True:
            # Clear other defaults and set this one
            for i, db in enumerate(databases):
                update_ops[f"databases.{i}.is_default"] = (i == db_index)
            update_ops["default_database_id"] = database_id

        if update_ops:
            await self.users.update_one({"_id": user["_id"]}, {"$set": update_ops})

        # Fetch updated user and return database
        updated_user = await self.users.find_one({"_id": user["_id"]})
        db_entry = updated_user["databases"][db_index]
        stats = await self.get_database_stats(user_id, database_id)

        return self.to_response(db_entry, user_id, stats)

    async def delete(self, database_id: str, user: dict) -> bool:
        """
        Delete a database with full cleanup.

        Args:
            database_id: Database identifier
            user: User document

        Returns:
            True if deleted successfully

        Raises:
            DatabaseNotFoundError: If database not found
            CannotDeleteError: If database is last or default
            DatabaseInUseError: If apps are using this database
        """
        from mongo_users import delete_mongo_user_for_database, update_viewer_user_roles

        user_id = str(user["_id"])
        databases = user.get("databases", [])

        # Cannot delete last database
        if len(databases) <= 1:
            raise CannotDeleteError("Cannot delete the last database")

        db_entry = self.get_database_entry(databases, database_id)

        # Cannot delete default database
        if db_entry.get("is_default"):
            raise CannotDeleteError(
                "Cannot delete the default database. Set another database as default first."
            )

        # Check if any apps use this database
        apps_using_db = await self.apps.count_documents({
            "user_id": user["_id"],
            "database_id": database_id,
            "status": {"$ne": "deleted"}
        })

        if apps_using_db > 0:
            raise DatabaseInUseError(apps_using_db)

        # Delete MongoDB user
        try:
            await delete_mongo_user_for_database(self.client, user_id, database_id)
        except Exception as e:
            logger.warning(f"Failed to delete MongoDB user for database {database_id}: {e}")

        # Drop the MongoDB database
        db_name = self.get_mongo_db_name(user_id, database_id)
        try:
            await self.client.drop_database(db_name)
            logger.info(f"Dropped MongoDB database {db_name}")
        except Exception as e:
            logger.warning(f"Failed to drop database {db_name}: {e}")

        # Remove from user's databases array
        await self.users.update_one(
            {"_id": user["_id"]},
            {"$pull": {"databases": {"id": database_id}}}
        )

        # Update viewer user to remove deleted database
        try:
            remaining_db_ids = [db["id"] for db in databases if db["id"] != database_id]
            await update_viewer_user_roles(self.client, user_id, remaining_db_ids)
        except Exception as e:
            logger.warning(f"Failed to update viewer user roles: {e}")

        return True

    # =========================================================================
    # Viewer Management
    # =========================================================================

    async def launch_viewer(self, user: dict, database_id: str = None) -> ViewerResponse:
        """
        Launch MongoDB viewer with access to user's databases.

        Args:
            user: User document
            database_id: Optional specific database ID (deprecated, always grants all-database access)

        Returns:
            ViewerResponse with credentials and status

        Raises:
            NoDatabasesError: If user has no databases
            DatabaseNotFoundError: If specific database_id not found
            ViewerLaunchError: If viewer deployment fails
        """
        from mongo_users import generate_mongo_password
        from deployment.viewer import create_mongo_viewer_resources, get_mongo_viewer_status

        user_id = str(user["_id"])
        databases = user.get("databases", [])

        if not databases:
            raise NoDatabasesError()

        # If specific database_id provided, validate it exists
        if database_id:
            self.get_database_entry(databases, database_id)

        # Generate viewer credentials
        viewer_username = "admin"
        viewer_password = generate_mongo_password()[:12]

        try:
            # Create/update viewer resources with all-database access
            await create_mongo_viewer_resources(
                user_id, user, viewer_username, viewer_password,
                use_viewer_user=True
            )

            # Get status
            status = await get_mongo_viewer_status(user_id)
            viewer_url = f"http://mongo-{user_id}.{self.app_domain}"

            return ViewerResponse(
                url=viewer_url,
                username=viewer_username,
                password=viewer_password,
                password_provided=True,
                ready=status.get("ready", False) if status else False,
                pod_status=status.get("pod_status") if status else None
            )
        except Exception as e:
            logger.error(f"Failed to launch viewer: {e}")
            raise ViewerLaunchError(str(e))


# Singleton instance for production use
database_service = DatabaseService()
