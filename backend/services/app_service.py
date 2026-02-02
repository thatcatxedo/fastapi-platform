"""
App management service for FastAPI Platform.

This service handles all app-related business logic including CRUD operations,
version management, draft handling, and deployment orchestration.
"""
import hashlib
import secrets
import string
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union

from models import AppCreate, AppUpdate, AppResponse, AppDetailResponse, DraftUpdate

logger = logging.getLogger(__name__)

# Maximum number of versions to keep in history
MAX_VERSION_HISTORY = 10


class AppServiceError(Exception):
    """Base exception for app service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AppNotFoundError(AppServiceError):
    """Raised when an app is not found."""
    def __init__(self, app_id: str):
        super().__init__("NOT_FOUND", f"App not found: {app_id}")


class ValidationError(AppServiceError):
    """Raised when code validation fails."""
    def __init__(self, message: str, line: int = None, file: str = None):
        details = {}
        if line is not None:
            details["line"] = line
        if file is not None:
            details["file"] = file
        super().__init__("VALIDATION_FAILED", message, details)


class InvalidRequestError(AppServiceError):
    """Raised for invalid request data."""
    def __init__(self, message: str):
        super().__init__("INVALID_REQUEST", message)


class InvalidDatabaseError(AppServiceError):
    """Raised when database_id is invalid."""
    def __init__(self):
        super().__init__("INVALID_DATABASE", "Database not found")


class DeploymentError(AppServiceError):
    """Raised when deployment fails."""
    def __init__(self, message: str):
        super().__init__("DEPLOY_FAILED", message)


class InvalidVersionError(AppServiceError):
    """Raised when version index is invalid."""
    def __init__(self, index: int, max_index: int):
        super().__init__(
            "INVALID_VERSION",
            f"Version index {index} is out of range (0-{max_index})"
        )


class AppService:
    """Service for app CRUD operations and version management."""

    def __init__(
        self,
        apps_collection=None,
        settings_collection=None,
        app_domain: str = None
    ):
        """
        Initialize AppService with optional dependency injection.

        Args:
            apps_collection: MongoDB collection for apps (uses default if None)
            settings_collection: MongoDB collection for settings (uses default if None)
            app_domain: Domain for app URLs (uses config default if None)
        """
        if apps_collection is None:
            from database import apps_collection as default_apps, settings_collection as default_settings
            self.apps = default_apps
            self.settings = default_settings
        else:
            self.apps = apps_collection
            self.settings = settings_collection

        if app_domain is None:
            from config import APP_DOMAIN
            self.app_domain = APP_DOMAIN
        else:
            self.app_domain = app_domain

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def compute_code_hash(code_or_files: Union[str, Dict[str, str]]) -> str:
        """
        Compute a short hash of code/files for comparison.

        Args:
            code_or_files: Either a string (single-file) or dict (multi-file)

        Returns:
            16-character hex hash string
        """
        if isinstance(code_or_files, dict):
            content = "".join(f"{k}:{v}" for k, v in sorted(code_or_files.items()))
        else:
            content = code_or_files or ""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def generate_app_id() -> str:
        """Generate a unique app_id (lowercase alphanumeric for K8s compliance)."""
        return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

    async def get_allowed_imports(self) -> Optional[set]:
        """
        Get allowed imports from settings, if overridden.

        Returns:
            Set of allowed import names, or None if using defaults
        """
        settings = await self.settings.find_one({"_id": "global"})
        allowed_imports = settings.get("allowed_imports") if settings else None
        if not allowed_imports:
            return None
        normalized = {
            item.strip().lower()
            for item in allowed_imports
            if isinstance(item, str) and item.strip()
        }
        return normalized or None

    def snapshot_version(self, app: dict) -> dict:
        """
        Create a version history entry from the current deployed state.

        Args:
            app: App document

        Returns:
            Version entry dict with code/files, deployed_at, and code_hash
        """
        mode = app.get("mode", "single")
        current_deployed_at = app.get("deployed_at") or app.get("last_deploy_at") or app["created_at"]

        if mode == "multi":
            current_deployed_files = app.get("deployed_files") or app.get("files", {})
            return {
                "files": current_deployed_files,
                "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
                "code_hash": self.compute_code_hash(current_deployed_files)
            }
        else:
            current_deployed_code = app.get("deployed_code") or app["code"]
            return {
                "code": current_deployed_code,
                "deployed_at": current_deployed_at.isoformat() if hasattr(current_deployed_at, 'isoformat') else str(current_deployed_at),
                "code_hash": self.compute_code_hash(current_deployed_code)
            }

    @staticmethod
    def add_version_to_history(app: dict, version_entry: dict) -> list:
        """
        Add a version entry to history and limit to MAX_VERSION_HISTORY entries.

        Args:
            app: App document
            version_entry: New version entry to add

        Returns:
            Updated version history list (most recent first)
        """
        version_history = app.get("version_history", [])
        version_history.insert(0, version_entry)
        return version_history[:MAX_VERSION_HISTORY]

    # =========================================================================
    # Response Builders
    # =========================================================================

    def to_response(self, app: dict) -> AppResponse:
        """
        Build an AppResponse from an app document.

        Args:
            app: App document from MongoDB

        Returns:
            AppResponse model instance
        """
        return AppResponse(
            id=str(app["_id"]),
            app_id=app["app_id"],
            name=app["name"],
            status=app["status"],
            created_at=app["created_at"].isoformat(),
            last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
            deployment_url=app["deployment_url"],
            error_message=app.get("error_message"),
            deploy_stage=app.get("deploy_stage"),
            last_error=app.get("last_error"),
            last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None
        )

    def to_detail_response(self, app: dict, has_unpublished_changes: bool) -> AppDetailResponse:
        """
        Build an AppDetailResponse from an app document.

        Args:
            app: App document from MongoDB
            has_unpublished_changes: Whether draft differs from deployed

        Returns:
            AppDetailResponse model instance
        """
        mode = app.get("mode", "single")

        return AppDetailResponse(
            id=str(app["_id"]),
            app_id=app["app_id"],
            name=app["name"],
            status=app["status"],
            created_at=app["created_at"].isoformat(),
            last_activity=app.get("last_activity").isoformat() if app.get("last_activity") else None,
            deployment_url=app["deployment_url"],
            error_message=app.get("error_message"),
            deploy_stage=app.get("deploy_stage"),
            last_error=app.get("last_error"),
            last_deploy_at=app.get("last_deploy_at").isoformat() if app.get("last_deploy_at") else None,
            # Single-file fields
            code=app.get("code") if mode == "single" else None,
            draft_code=app.get("draft_code") if mode == "single" else None,
            deployed_code=app.get("deployed_code") if mode == "single" else None,
            # Multi-file fields
            mode=mode,
            framework=app.get("framework"),
            entrypoint=app.get("entrypoint"),
            files=app.get("files") if mode == "multi" else None,
            draft_files=app.get("draft_files") if mode == "multi" else None,
            deployed_files=app.get("deployed_files") if mode == "multi" else None,
            # Common fields
            env_vars=app.get("env_vars"),
            deployed_at=app.get("deployed_at").isoformat() if app.get("deployed_at") else None,
            has_unpublished_changes=has_unpublished_changes,
            database_id=app.get("database_id")
        )

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_by_app_id(self, app_id: str, user: dict) -> dict:
        """
        Fetch an app by app_id for the given user.

        Args:
            app_id: The app's unique identifier
            user: User document

        Returns:
            App document

        Raises:
            AppNotFoundError: If app doesn't exist or doesn't belong to user
        """
        app = await self.apps.find_one({"app_id": app_id, "user_id": user["_id"]})
        if not app:
            raise AppNotFoundError(app_id)
        return app

    async def list_for_user(self, user: dict) -> List[dict]:
        """
        List all non-deleted apps for a user.

        Args:
            user: User document

        Returns:
            List of app documents
        """
        apps = []
        async for app in self.apps.find({"user_id": user["_id"], "status": {"$ne": "deleted"}}):
            apps.append(app)
        return apps

    async def get_with_changes_flag(self, app_id: str, user: dict) -> Tuple[dict, bool]:
        """
        Get an app and compute whether it has unpublished changes.

        Args:
            app_id: The app's unique identifier
            user: User document

        Returns:
            Tuple of (app document, has_unpublished_changes boolean)
        """
        app = await self.get_by_app_id(app_id, user)
        mode = app.get("mode", "single")

        if mode == "multi":
            deployed_files = app.get("deployed_files") or app.get("files", {})
            draft_files = app.get("draft_files")
            current_files = draft_files if draft_files is not None else app.get("files", {})
            has_unpublished_changes = self.compute_code_hash(current_files) != self.compute_code_hash(deployed_files)
        else:
            # Migration for legacy apps without deployed_code
            deployed_code = app.get("deployed_code")
            if deployed_code is None:
                deployed_code = app["code"]
                await self.apps.update_one(
                    {"_id": app["_id"]},
                    {"$set": {"deployed_code": deployed_code, "deployed_at": app.get("last_deploy_at") or app["created_at"]}}
                )
                app["deployed_code"] = deployed_code

            draft_code = app.get("draft_code")
            current_code = draft_code if draft_code is not None else app["code"]
            has_unpublished_changes = self.compute_code_hash(current_code) != self.compute_code_hash(deployed_code)

        return app, has_unpublished_changes

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def validate_database_access(self, database_id: str, user: dict) -> None:
        """
        Validate that user has access to the specified database.

        Args:
            database_id: Database ID to validate
            user: User document

        Raises:
            InvalidDatabaseError: If database not found for user
        """
        if database_id:
            databases = user.get("databases", [])
            if not any(db["id"] == database_id for db in databases):
                raise InvalidDatabaseError()

    async def validate_code_or_files(
        self,
        mode: str,
        code: str = None,
        files: dict = None,
        entrypoint: str = "app.py",
        framework: str = None
    ) -> None:
        """
        Validate code or files based on mode.

        Args:
            mode: "single" or "multi"
            code: Code string for single-file mode
            files: Files dict for multi-file mode
            entrypoint: Entry point file for multi-file mode
            framework: Framework type for multi-file mode

        Raises:
            InvalidRequestError: If required fields missing
            ValidationError: If code validation fails
        """
        from validation import validate_code, validate_multifile

        allowed_imports = await self.get_allowed_imports()

        if mode == "multi":
            if not files:
                raise InvalidRequestError("files required for multi-file mode")
            if not framework:
                raise InvalidRequestError("framework required for multi-file mode")
            if framework not in ("fastapi", "fasthtml"):
                raise InvalidRequestError("framework must be 'fastapi' or 'fasthtml'")

            is_valid, error_msg, error_line, error_file = validate_multifile(
                files, entrypoint, allowed_imports_override=allowed_imports
            )
            if not is_valid:
                raise ValidationError(f"Code validation failed: {error_msg}", error_line, error_file)
        else:
            if not code:
                raise InvalidRequestError("code required for single-file mode")

            is_valid, error_msg, error_line = validate_code(
                code, allowed_imports_override=allowed_imports
            )
            if not is_valid:
                raise ValidationError(f"Code validation failed: {error_msg}", error_line)

    # =========================================================================
    # Deployment
    # =========================================================================

    async def deploy(
        self,
        app_doc: dict,
        user: dict,
        is_create: bool = False,
        new_deployed_content: Union[str, dict] = None
    ) -> None:
        """
        Deploy an app and update its status in the database.

        Args:
            app_doc: App document
            user: User document
            is_create: True if creating new deployment, False if updating
            new_deployed_content: New code/files to mark as deployed

        Raises:
            DeploymentError: If deployment fails
        """
        from deployment import create_app_deployment, update_app_deployment
        from utils import friendly_k8s_error

        try:
            if is_create:
                await create_app_deployment(app_doc, user)
            else:
                await update_app_deployment(app_doc, user)

            mode = app_doc.get("mode", "single")

            success_update = {
                "status": "running",
                "deploy_stage": "running",
                "last_error": None
            }

            if new_deployed_content is not None:
                if mode == "multi":
                    success_update["deployed_files"] = new_deployed_content
                    success_update["draft_files"] = None
                else:
                    success_update["deployed_code"] = new_deployed_content
                    success_update["draft_code"] = None
                success_update["deployed_at"] = datetime.utcnow()

            await self.apps.update_one(
                {"_id": app_doc["_id"]},
                {"$set": success_update}
            )
        except Exception as e:
            error_msg = friendly_k8s_error(str(e))
            await self.apps.update_one(
                {"_id": app_doc["_id"]},
                {"$set": {"status": "error", "deploy_stage": "error", "error_message": error_msg, "last_error": error_msg}}
            )
            raise DeploymentError(error_msg)

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create(self, app_data: AppCreate, user: dict) -> dict:
        """
        Create a new app with validation and deployment.

        Args:
            app_data: App creation data
            user: User document

        Returns:
            Created app document

        Raises:
            InvalidDatabaseError: If database_id is invalid
            InvalidRequestError: If required fields missing
            ValidationError: If code validation fails
            DeploymentError: If deployment fails
        """
        mode = app_data.mode or "single"

        # Validate database access
        self.validate_database_access(app_data.database_id, user)

        # Validate code/files
        await self.validate_code_or_files(
            mode=mode,
            code=app_data.code,
            files=app_data.files,
            entrypoint=app_data.entrypoint or "app.py",
            framework=app_data.framework
        )

        # Generate unique app_id
        app_id = self.generate_app_id()

        # Create app document
        now = datetime.utcnow()
        app_doc = {
            "user_id": user["_id"],
            "app_id": app_id,
            "name": app_data.name,
            "mode": mode,
            "env_vars": app_data.env_vars or {},
            "database_id": app_data.database_id,
            "status": "deploying",
            "deploy_stage": "deploying",
            "last_error": None,
            "last_deploy_at": now,
            "created_at": now,
            "last_activity": now,
            "deployment_url": f"https://app-{app_id}.{self.app_domain}",
            "version_history": []
        }

        if mode == "multi":
            app_doc["framework"] = app_data.framework
            app_doc["entrypoint"] = app_data.entrypoint or "app.py"
            app_doc["files"] = app_data.files
            app_doc["deployed_files"] = app_data.files
            app_doc["deployed_at"] = now
            app_doc["draft_files"] = None
        else:
            app_doc["code"] = app_data.code
            app_doc["deployed_code"] = app_data.code
            app_doc["deployed_at"] = now
            app_doc["draft_code"] = None

        result = await self.apps.insert_one(app_doc)
        app_doc["_id"] = result.inserted_id

        # Deploy to Kubernetes
        await self.deploy(app_doc, user, is_create=True)

        return await self.apps.find_one({"_id": result.inserted_id})

    async def update(self, app_id: str, app_data: AppUpdate, user: dict) -> dict:
        """
        Update an existing app.

        Args:
            app_id: App identifier
            app_data: Update data
            user: User document

        Returns:
            Updated app document

        Raises:
            AppNotFoundError: If app not found
            InvalidDatabaseError: If database_id is invalid
            ValidationError: If code validation fails
            DeploymentError: If deployment fails
        """
        app = await self.get_by_app_id(app_id, user)
        mode = app.get("mode", "single")

        update_data = {}
        needs_redeploy = False
        new_deployed_content = None

        if app_data.name is not None:
            update_data["name"] = app_data.name

        # Handle code/files update based on mode
        if mode == "multi":
            if app_data.files is not None:
                await self.validate_code_or_files(
                    mode="multi",
                    files=app_data.files,
                    entrypoint=app.get("entrypoint", "app.py"),
                    framework=app.get("framework")
                )
                update_data["files"] = app_data.files
                new_deployed_content = app_data.files
                needs_redeploy = True
        else:
            if app_data.code is not None:
                await self.validate_code_or_files(mode="single", code=app_data.code)
                update_data["code"] = app_data.code
                new_deployed_content = app_data.code
                needs_redeploy = True

        if app_data.env_vars is not None:
            update_data["env_vars"] = app_data.env_vars
            needs_redeploy = True

        # Handle database_id change
        if app_data.database_id is not None:
            self.validate_database_access(app_data.database_id, user)
            update_data["database_id"] = app_data.database_id
            needs_redeploy = True

        if needs_redeploy:
            update_data["status"] = "deploying"
            update_data["deploy_stage"] = "deploying"
            update_data["last_error"] = None
            update_data["last_deploy_at"] = datetime.utcnow()

            # Snapshot current deployed code/files to version history
            version_entry = self.snapshot_version(app)
            update_data["version_history"] = self.add_version_to_history(app, version_entry)

        if not update_data:
            raise InvalidRequestError("No fields to update")

        await self.apps.update_one({"_id": app["_id"]}, {"$set": update_data})

        if needs_redeploy:
            updated_app = await self.apps.find_one({"_id": app["_id"]})
            await self.deploy(updated_app, user, is_create=False, new_deployed_content=new_deployed_content)

        return await self.apps.find_one({"_id": app["_id"]})

    async def delete(self, app_id: str, user: dict) -> bool:
        """
        Delete an app (soft delete + K8s cleanup).

        Args:
            app_id: App identifier
            user: User document

        Returns:
            True if deleted successfully
        """
        from deployment import delete_app_deployment

        app = await self.get_by_app_id(app_id, user)

        # Delete from Kubernetes
        try:
            await delete_app_deployment(app, user)
        except Exception as e:
            logger.error(f"Error deleting deployment: {e}")

        # Mark as deleted in database
        await self.apps.update_one(
            {"_id": app["_id"]},
            {"$set": {"status": "deleted"}}
        )

        return True

    async def clone(self, app_id: str, user: dict) -> dict:
        """
        Clone an existing app.

        Args:
            app_id: Source app identifier
            user: User document

        Returns:
            Cloned app document
        """
        source_app = await self.get_by_app_id(app_id, user)
        mode = source_app.get("mode", "single")

        # Generate unique app_id for the clone
        new_app_id = self.generate_app_id()

        # Clone name with "-copy" suffix
        base_name = source_app["name"]
        if base_name.endswith("-copy"):
            base_name = base_name[:-5]
        new_name = f"{base_name}-copy"

        # Clone env vars but clear values
        cloned_env_vars = {}
        if source_app.get("env_vars"):
            for key in source_app["env_vars"].keys():
                cloned_env_vars[key] = ""

        now = datetime.utcnow()
        cloned_app_doc = {
            "user_id": user["_id"],
            "app_id": new_app_id,
            "name": new_name,
            "mode": mode,
            "env_vars": cloned_env_vars,
            "status": "deploying",
            "deploy_stage": "deploying",
            "last_error": None,
            "last_deploy_at": now,
            "created_at": now,
            "last_activity": now,
            "deployment_url": f"https://app-{new_app_id}.{self.app_domain}",
            "version_history": []
        }

        if mode == "multi":
            cloned_files = source_app.get("files", {})
            await self.validate_code_or_files(
                mode="multi",
                files=cloned_files,
                entrypoint=source_app.get("entrypoint", "app.py"),
                framework=source_app.get("framework")
            )
            cloned_app_doc["framework"] = source_app.get("framework")
            cloned_app_doc["entrypoint"] = source_app.get("entrypoint", "app.py")
            cloned_app_doc["files"] = cloned_files
            cloned_app_doc["deployed_files"] = cloned_files
            cloned_app_doc["deployed_at"] = now
            cloned_app_doc["draft_files"] = None
        else:
            cloned_code = source_app["code"]
            await self.validate_code_or_files(mode="single", code=cloned_code)
            cloned_app_doc["code"] = cloned_code
            cloned_app_doc["deployed_code"] = cloned_code
            cloned_app_doc["deployed_at"] = now
            cloned_app_doc["draft_code"] = None

        result = await self.apps.insert_one(cloned_app_doc)
        cloned_app_doc["_id"] = result.inserted_id

        await self.deploy(cloned_app_doc, user, is_create=True)

        return await self.apps.find_one({"_id": result.inserted_id})

    # =========================================================================
    # Draft Handling
    # =========================================================================

    async def save_draft(self, app_id: str, draft: DraftUpdate, user: dict) -> Tuple[dict, bool]:
        """
        Save draft code/files without deploying.

        Args:
            app_id: App identifier
            draft: Draft update data
            user: User document

        Returns:
            Tuple of (updated app document, has_unpublished_changes)
        """
        app = await self.get_by_app_id(app_id, user)
        mode = app.get("mode", "single")

        if mode == "multi":
            if not draft.files:
                raise InvalidRequestError("files required for multi-file mode draft")

            await self.validate_code_or_files(
                mode="multi",
                files=draft.files,
                entrypoint=app.get("entrypoint", "app.py"),
                framework=app.get("framework")
            )

            await self.apps.update_one(
                {"_id": app["_id"]},
                {"$set": {
                    "files": draft.files,
                    "draft_files": draft.files,
                    "last_activity": datetime.utcnow()
                }}
            )

            updated_app = await self.apps.find_one({"_id": app["_id"]})
            deployed_files = updated_app.get("deployed_files") or updated_app.get("files", {})
            has_unpublished_changes = self.compute_code_hash(draft.files) != self.compute_code_hash(deployed_files)
        else:
            if not draft.code:
                raise InvalidRequestError("code required for single-file mode draft")

            await self.validate_code_or_files(mode="single", code=draft.code)

            await self.apps.update_one(
                {"_id": app["_id"]},
                {"$set": {
                    "code": draft.code,
                    "draft_code": draft.code,
                    "last_activity": datetime.utcnow()
                }}
            )

            updated_app = await self.apps.find_one({"_id": app["_id"]})
            deployed_code = updated_app.get("deployed_code") or updated_app["code"]
            has_unpublished_changes = self.compute_code_hash(draft.code) != self.compute_code_hash(deployed_code)

        return updated_app, has_unpublished_changes

    # =========================================================================
    # Version Management
    # =========================================================================

    async def get_versions(self, app_id: str, user: dict) -> Tuple[List[dict], str]:
        """
        Get version history for an app.

        Args:
            app_id: App identifier
            user: User document

        Returns:
            Tuple of (version history list, current deployed hash)
        """
        app = await self.get_by_app_id(app_id, user)
        mode = app.get("mode", "single")

        version_history = app.get("version_history", [])

        if mode == "multi":
            deployed_content = app.get("deployed_files") or app.get("files", {})
        else:
            deployed_content = app.get("deployed_code") or app.get("code", "")

        current_hash = self.compute_code_hash(deployed_content)

        return version_history, current_hash

    async def rollback(self, app_id: str, version_index: int, user: dict) -> dict:
        """
        Rollback to a previous version.

        Args:
            app_id: App identifier
            version_index: Index in version history to rollback to
            user: User document

        Returns:
            Updated app document

        Raises:
            InvalidVersionError: If version_index is out of range
        """
        app = await self.get_by_app_id(app_id, user)
        mode = app.get("mode", "single")

        version_history = app.get("version_history", [])

        if version_index < 0 or version_index >= len(version_history):
            max_index = len(version_history) - 1 if version_history else 0
            raise InvalidVersionError(version_index, max_index)

        rollback_version = version_history[version_index]

        # Snapshot current deployed content before rollback
        version_entry = self.snapshot_version(app)
        new_version_history = self.add_version_to_history(app, version_entry)

        now = datetime.utcnow()
        update_set = {
            "status": "deploying",
            "deploy_stage": "deploying",
            "last_error": None,
            "last_deploy_at": now,
            "version_history": new_version_history
        }

        if mode == "multi":
            rollback_files = rollback_version.get("files", {})
            await self.validate_code_or_files(
                mode="multi",
                files=rollback_files,
                entrypoint=app.get("entrypoint", "app.py"),
                framework=app.get("framework")
            )
            update_set["files"] = rollback_files
            new_deployed_content = rollback_files
        else:
            rollback_code = rollback_version.get("code", "")
            await self.validate_code_or_files(mode="single", code=rollback_code)
            update_set["code"] = rollback_code
            new_deployed_content = rollback_code

        await self.apps.update_one({"_id": app["_id"]}, {"$set": update_set})

        updated_app = await self.apps.find_one({"_id": app["_id"]})
        await self.deploy(updated_app, user, is_create=False, new_deployed_content=new_deployed_content)

        return await self.apps.find_one({"_id": app["_id"]})

    # =========================================================================
    # Activity Tracking
    # =========================================================================

    async def record_activity(self, app_id: str, user: dict) -> None:
        """
        Record activity timestamp for an app.

        Args:
            app_id: App identifier
            user: User document
        """
        app = await self.get_by_app_id(app_id, user)
        await self.apps.update_one(
            {"_id": app["_id"]},
            {"$set": {"last_activity": datetime.utcnow()}}
        )


# Singleton instance for production use
app_service = AppService()
