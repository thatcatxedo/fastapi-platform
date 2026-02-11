"""
Template service for FastAPI Platform.

This service handles template CRUD operations including access control,
validation, and response building.
"""
import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

from models import TemplateResponse, TemplateCreate, TemplateUpdate

logger = logging.getLogger(__name__)


class TemplateServiceError(Exception):
    """Base exception for template service errors."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TemplateNotFoundError(TemplateServiceError):
    """Raised when a template is not found."""
    def __init__(self, template_id: str):
        super().__init__("NOT_FOUND", f"Template not found: {template_id}")


class AccessDeniedError(TemplateServiceError):
    """Raised when user doesn't have access to a template."""
    def __init__(self):
        super().__init__("ACCESS_DENIED", "Access denied")


class CannotEditGlobalError(TemplateServiceError):
    """Raised when trying to edit a global template."""
    def __init__(self):
        super().__init__("CANNOT_EDIT_GLOBAL", "Cannot edit global templates")


class CannotDeleteGlobalError(TemplateServiceError):
    """Raised when trying to delete a global template."""
    def __init__(self):
        super().__init__("CANNOT_DELETE_GLOBAL", "Cannot delete global templates")


class InvalidTemplateError(TemplateServiceError):
    """Raised when template data is invalid."""
    def __init__(self, reason: str):
        super().__init__("INVALID_TEMPLATE", reason)


class DuplicateTemplateNameError(TemplateServiceError):
    """Raised when template name already exists."""
    def __init__(self):
        super().__init__("DUPLICATE_NAME", "You already have a template with this name")


class NoFieldsToUpdateError(TemplateServiceError):
    """Raised when no fields provided for update."""
    def __init__(self):
        super().__init__("NO_FIELDS", "No fields to update")


class TemplateService:
    """Service for template CRUD operations and access control."""

    def __init__(self, templates_collection=None):
        """
        Initialize TemplateService with optional dependency injection.
        """
        if templates_collection is None:
            from database import templates_collection as default_templates
            self.templates = default_templates
        else:
            self.templates = templates_collection

    # =========================================================================
    # Response Builder
    # =========================================================================

    @staticmethod
    def to_response(t: dict) -> TemplateResponse:
        """
        Convert MongoDB template document to response model.

        Args:
            t: Template document from MongoDB

        Returns:
            TemplateResponse model instance
        """
        return TemplateResponse(
            id=str(t["_id"]),
            name=t["name"],
            description=t["description"],
            code=t.get("code"),
            mode=t.get("mode", "single"),
            framework=t.get("framework"),
            entrypoint=t.get("entrypoint"),
            files=t.get("files"),
            complexity=t["complexity"],
            is_global=t["is_global"],
            created_at=t["created_at"].isoformat() if isinstance(t.get("created_at"), datetime) else t.get("created_at", ""),
            tags=t.get("tags", []),
            user_id=str(t["user_id"]) if t.get("user_id") else None,
            requires_database=t.get("requires_database", False),
            is_hidden=t.get("is_hidden", False)
        )

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_template_data(self, data: TemplateCreate) -> None:
        """
        Validate template creation data.

        Raises:
            InvalidTemplateError: If data is invalid
        """
        from validation import validate_code, validate_multifile

        if not data.name or not data.name.strip():
            raise InvalidTemplateError("Template name is required")

        if data.complexity not in ("simple", "medium", "complex"):
            raise InvalidTemplateError("Complexity must be 'simple', 'medium', or 'complex'")

        if data.mode not in ("single", "multi"):
            raise InvalidTemplateError("Mode must be 'single' or 'multi'")

        if data.mode == "single":
            if not data.code:
                raise InvalidTemplateError("Single-file templates require code")
            is_valid, error_msg, _ = validate_code(data.code)
            if not is_valid:
                raise InvalidTemplateError(f"Invalid template code: {error_msg}")
        else:
            if not data.files:
                raise InvalidTemplateError("Multi-file templates require files")
            if not data.framework:
                raise InvalidTemplateError("Multi-file templates require framework (fastapi or fasthtml)")
            is_valid, error_msg, _, _ = validate_multifile(
                data.files,
                data.entrypoint or "app.py"
            )
            if not is_valid:
                raise InvalidTemplateError(f"Invalid template code: {error_msg}")

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def list_for_user(self, user: dict) -> List[TemplateResponse]:
        """
        List all templates accessible to a user (global + user's own).
        Filters out admin-hidden templates and per-user hidden templates.

        Args:
            user: User document

        Returns:
            List of TemplateResponse
        """
        # Build exclusion list from user's hidden preferences
        hidden_ids = user.get("hidden_templates", [])
        hidden_oids = []
        for tid in hidden_ids:
            try:
                hidden_oids.append(ObjectId(tid))
            except Exception:
                pass

        # Get global templates (exclude admin-hidden and user-hidden)
        global_query = {"is_global": True, "is_hidden": {"$ne": True}}
        if hidden_oids:
            global_query["_id"] = {"$nin": hidden_oids}
        global_templates = await self.templates.find(global_query).to_list(length=100)

        # Get user's templates (exclude user-hidden)
        user_query = {"is_global": False, "user_id": user["_id"]}
        if hidden_oids:
            user_query["_id"] = {"$nin": hidden_oids}
        user_templates = await self.templates.find(user_query).to_list(length=100)

        all_templates = global_templates + user_templates
        return [self.to_response(t) for t in all_templates]

    async def list_all(self) -> List[TemplateResponse]:
        """List ALL templates (admin view, no filtering)."""
        all_templates = await self.templates.find().sort("created_at", -1).to_list(length=500)
        return [self.to_response(t) for t in all_templates]

    async def get_by_id(self, template_id: str, user: dict) -> dict:
        """
        Get a template by ID with access check.

        Args:
            template_id: Template identifier
            user: User document

        Returns:
            Template document

        Raises:
            TemplateNotFoundError: If template doesn't exist
            AccessDeniedError: If user can't access template
        """
        try:
            template = await self.templates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise TemplateNotFoundError(template_id)

        if not template:
            raise TemplateNotFoundError(template_id)

        # Check access: global templates or user's own
        if not template.get("is_global") and str(template.get("user_id")) != str(user["_id"]):
            raise AccessDeniedError()

        return template

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create(self, data: TemplateCreate, user: dict) -> TemplateResponse:
        """
        Create a new user template.

        Args:
            data: Template creation data
            user: User document

        Returns:
            Created TemplateResponse

        Raises:
            InvalidTemplateError: If template data is invalid
            DuplicateTemplateNameError: If name already exists for user
        """
        # Validate template data
        self._validate_template_data(data)

        # Check for duplicate name
        existing = await self.templates.find_one({
            "name": data.name,
            "is_global": False,
            "user_id": user["_id"]
        })
        if existing:
            raise DuplicateTemplateNameError()

        # Create template document
        template_doc = {
            "name": data.name.strip(),
            "description": data.description or "",
            "mode": data.mode,
            "complexity": data.complexity,
            "tags": data.tags or [],
            "is_global": False,
            "user_id": user["_id"],
            "created_at": datetime.utcnow(),
        }

        # Add mode-specific fields
        if data.mode == "single":
            template_doc["code"] = data.code
            template_doc["files"] = None
            template_doc["framework"] = None
            template_doc["entrypoint"] = None
        else:
            template_doc["code"] = None
            template_doc["files"] = data.files
            template_doc["framework"] = data.framework
            template_doc["entrypoint"] = data.entrypoint or "app.py"

        result = await self.templates.insert_one(template_doc)
        template_doc["_id"] = result.inserted_id

        return self.to_response(template_doc)

    async def update(self, template_id: str, data: TemplateUpdate, user: dict, is_admin: bool = False) -> TemplateResponse:
        """
        Update an existing user template.

        Args:
            template_id: Template identifier
            data: Update data
            user: User document

        Returns:
            Updated TemplateResponse

        Raises:
            TemplateNotFoundError: If template doesn't exist
            CannotEditGlobalError: If trying to edit global template
            AccessDeniedError: If user doesn't own template
            InvalidTemplateError: If update data is invalid
            DuplicateTemplateNameError: If new name already exists
            NoFieldsToUpdateError: If no fields provided
        """
        from validation import validate_code, validate_multifile

        try:
            template = await self.templates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise TemplateNotFoundError(template_id)

        if not template:
            raise TemplateNotFoundError(template_id)

        # Check ownership
        if template.get("is_global"):
            if not is_admin:
                raise CannotEditGlobalError()
        else:
            if str(template.get("user_id")) != str(user["_id"]) and not is_admin:
                raise AccessDeniedError()

        # Build update fields
        update_fields = {}

        # Handle is_hidden (admin only, from AdminTemplateUpdate)
        if hasattr(data, 'is_hidden') and data.is_hidden is not None:
            update_fields["is_hidden"] = data.is_hidden

        if data.name is not None:
            if not data.name.strip():
                raise InvalidTemplateError("Template name cannot be empty")
            # Check for duplicate name
            if data.name != template["name"]:
                existing = await self.templates.find_one({
                    "name": data.name,
                    "is_global": False,
                    "user_id": user["_id"],
                    "_id": {"$ne": ObjectId(template_id)}
                })
                if existing:
                    raise DuplicateTemplateNameError()
            update_fields["name"] = data.name.strip()

        if data.description is not None:
            update_fields["description"] = data.description

        if data.complexity is not None:
            if data.complexity not in ("simple", "medium", "complex"):
                raise InvalidTemplateError("Complexity must be 'simple', 'medium', or 'complex'")
            update_fields["complexity"] = data.complexity

        if data.tags is not None:
            update_fields["tags"] = data.tags

        # Handle code update (single-file mode)
        if data.code is not None:
            if template.get("mode") != "single":
                raise InvalidTemplateError("Cannot set code on multi-file template")
            is_valid, error_msg, _ = validate_code(data.code)
            if not is_valid:
                raise InvalidTemplateError(f"Invalid template code: {error_msg}")
            update_fields["code"] = data.code

        # Handle files update (multi-file mode)
        if data.files is not None:
            if template.get("mode") != "multi":
                raise InvalidTemplateError("Cannot set files on single-file template")
            is_valid, error_msg, _, _ = validate_multifile(
                data.files,
                template.get("entrypoint", "app.py")
            )
            if not is_valid:
                raise InvalidTemplateError(f"Invalid template code: {error_msg}")
            update_fields["files"] = data.files

        if not update_fields:
            raise NoFieldsToUpdateError()

        await self.templates.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": update_fields}
        )

        updated = await self.templates.find_one({"_id": ObjectId(template_id)})
        return self.to_response(updated)

    async def delete(self, template_id: str, user: dict, is_admin: bool = False) -> bool:
        """
        Delete a template.

        Args:
            template_id: Template identifier
            user: User document
            is_admin: If True, bypass global/ownership checks

        Returns:
            True if deleted

        Raises:
            TemplateNotFoundError: If template doesn't exist
            CannotDeleteGlobalError: If trying to delete global template
            AccessDeniedError: If user doesn't own template
        """
        try:
            template = await self.templates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise TemplateNotFoundError(template_id)

        if not template:
            raise TemplateNotFoundError(template_id)

        # Check ownership
        if template.get("is_global"):
            if not is_admin:
                raise CannotDeleteGlobalError()
        else:
            if str(template.get("user_id")) != str(user["_id"]) and not is_admin:
                raise AccessDeniedError()

        await self.templates.delete_one({"_id": ObjectId(template_id)})
        return True

    # =========================================================================
    # User Hiding
    # =========================================================================

    async def hide_for_user(self, template_id: str, user: dict) -> None:
        """Add template to user's hidden list."""
        from database import users_collection
        try:
            template = await self.templates.find_one({"_id": ObjectId(template_id)})
        except Exception:
            raise TemplateNotFoundError(template_id)
        if not template:
            raise TemplateNotFoundError(template_id)

        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$addToSet": {"hidden_templates": template_id}}
        )

    async def unhide_for_user(self, template_id: str, user: dict) -> None:
        """Remove template from user's hidden list."""
        from database import users_collection
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$pull": {"hidden_templates": template_id}}
        )


# Singleton instance for production use
template_service = TemplateService()
