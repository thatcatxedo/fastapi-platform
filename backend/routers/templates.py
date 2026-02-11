"""
Template routes for FastAPI Platform.

This module contains thin HTTP handlers that delegate to TemplateService
for all business logic.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from models import TemplateResponse, TemplateCreate, TemplateUpdate
from auth import get_current_user
from services.template_service import (
    template_service,
    TemplateServiceError,
    TemplateNotFoundError,
    AccessDeniedError,
    CannotEditGlobalError,
    CannotDeleteGlobalError,
    InvalidTemplateError,
    DuplicateTemplateNameError,
    NoFieldsToUpdateError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


def handle_service_error(e: TemplateServiceError) -> HTTPException:
    """Convert service exceptions to HTTP exceptions."""
    status_map = {
        "NOT_FOUND": 404,
        "ACCESS_DENIED": 403,
        "CANNOT_EDIT_GLOBAL": 403,
        "CANNOT_DELETE_GLOBAL": 403,
        "INVALID_TEMPLATE": 400,
        "DUPLICATE_NAME": 400,
        "NO_FIELDS": 400,
    }
    status_code = status_map.get(e.code, 500)
    return HTTPException(
        status_code=status_code,
        detail=e.message
    )


# =============================================================================
# List and Get
# =============================================================================

@router.get("", response_model=List[TemplateResponse])
async def list_templates(user: dict = Depends(get_current_user)):
    """List all templates (global + user's templates)."""
    return await template_service.list_for_user(user)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    """Get a specific template."""
    try:
        template = await template_service.get_by_id(template_id, user)
        return template_service.to_response(template)
    except TemplateServiceError as e:
        raise handle_service_error(e)


# =============================================================================
# Create, Update, Delete
# =============================================================================

@router.post("", response_model=TemplateResponse)
async def create_template(template_data: TemplateCreate, user: dict = Depends(get_current_user)):
    """Create a new user template."""
    try:
        return await template_service.create(template_data, user)
    except TemplateServiceError as e:
        raise handle_service_error(e)


@router.post("/{template_id}/hide")
async def hide_template(template_id: str, user: dict = Depends(get_current_user)):
    """Hide a template for the current user."""
    try:
        await template_service.hide_for_user(template_id, user)
        return {"success": True}
    except TemplateServiceError as e:
        raise handle_service_error(e)


@router.post("/{template_id}/unhide")
async def unhide_template(template_id: str, user: dict = Depends(get_current_user)):
    """Unhide a template for the current user."""
    try:
        await template_service.unhide_for_user(template_id, user)
        return {"success": True}
    except TemplateServiceError as e:
        raise handle_service_error(e)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing user template."""
    try:
        return await template_service.update(template_id, template_data, user)
    except TemplateServiceError as e:
        raise handle_service_error(e)


@router.delete("/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    """Delete a user template."""
    try:
        await template_service.delete(template_id, user)
        return {"success": True, "deleted_id": template_id}
    except TemplateServiceError as e:
        raise handle_service_error(e)
