"""
Template routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from bson import ObjectId

from models import TemplateResponse, TemplateCreate, TemplateUpdate
from auth import get_current_user
from database import templates_collection
from validation import validate_code, validate_multifile

router = APIRouter(prefix="/api/templates", tags=["templates"])


def template_to_response(t: dict) -> TemplateResponse:
    """Convert MongoDB template document to response model"""
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
        user_id=str(t["user_id"]) if t.get("user_id") else None
    )


@router.get("", response_model=List[TemplateResponse])
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
    return [template_to_response(t) for t in all_templates]


@router.get("/{template_id}", response_model=TemplateResponse)
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

    return template_to_response(template)


@router.post("", response_model=TemplateResponse)
async def create_template(template_data: TemplateCreate, user: dict = Depends(get_current_user)):
    """Create a new user template"""
    # Validate template name
    if not template_data.name or not template_data.name.strip():
        raise HTTPException(status_code=400, detail="Template name is required")

    # Validate complexity
    if template_data.complexity not in ("simple", "medium", "complex"):
        raise HTTPException(status_code=400, detail="Complexity must be 'simple', 'medium', or 'complex'")

    # Validate mode
    if template_data.mode not in ("single", "multi"):
        raise HTTPException(status_code=400, detail="Mode must be 'single' or 'multi'")

    # Validate code/files based on mode
    if template_data.mode == "single":
        if not template_data.code:
            raise HTTPException(status_code=400, detail="Single-file templates require code")
        # Validate the code
        validation = validate_code(template_data.code)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid template code: {validation['error']}")
    else:
        if not template_data.files:
            raise HTTPException(status_code=400, detail="Multi-file templates require files")
        if not template_data.framework:
            raise HTTPException(status_code=400, detail="Multi-file templates require framework (fastapi or fasthtml)")
        # Validate the files
        validation = validate_multifile(template_data.files, template_data.entrypoint or "app.py", template_data.framework)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid template code: {validation['error']}")

    # Check for duplicate name for this user
    existing = await templates_collection.find_one({
        "name": template_data.name,
        "is_global": False,
        "user_id": user["_id"]
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a template with this name")

    # Create template document
    template_doc = {
        "name": template_data.name.strip(),
        "description": template_data.description or "",
        "mode": template_data.mode,
        "complexity": template_data.complexity,
        "tags": template_data.tags or [],
        "is_global": False,
        "user_id": user["_id"],
        "created_at": datetime.utcnow(),
    }

    # Add mode-specific fields
    if template_data.mode == "single":
        template_doc["code"] = template_data.code
        template_doc["files"] = None
        template_doc["framework"] = None
        template_doc["entrypoint"] = None
    else:
        template_doc["code"] = None
        template_doc["files"] = template_data.files
        template_doc["framework"] = template_data.framework
        template_doc["entrypoint"] = template_data.entrypoint or "app.py"

    result = await templates_collection.insert_one(template_doc)
    template_doc["_id"] = result.inserted_id

    return template_to_response(template_doc)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an existing user template"""
    try:
        template = await templates_collection.find_one({"_id": ObjectId(template_id)})
    except:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check ownership - cannot edit global templates or other users' templates
    if template.get("is_global"):
        raise HTTPException(status_code=403, detail="Cannot edit global templates")
    if str(template.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    # Build update fields
    update_fields = {}

    if template_data.name is not None:
        if not template_data.name.strip():
            raise HTTPException(status_code=400, detail="Template name cannot be empty")
        # Check for duplicate name
        if template_data.name != template["name"]:
            existing = await templates_collection.find_one({
                "name": template_data.name,
                "is_global": False,
                "user_id": user["_id"],
                "_id": {"$ne": ObjectId(template_id)}
            })
            if existing:
                raise HTTPException(status_code=400, detail="You already have a template with this name")
        update_fields["name"] = template_data.name.strip()

    if template_data.description is not None:
        update_fields["description"] = template_data.description

    if template_data.complexity is not None:
        if template_data.complexity not in ("simple", "medium", "complex"):
            raise HTTPException(status_code=400, detail="Complexity must be 'simple', 'medium', or 'complex'")
        update_fields["complexity"] = template_data.complexity

    if template_data.tags is not None:
        update_fields["tags"] = template_data.tags

    # Handle code update (single-file mode)
    if template_data.code is not None:
        if template.get("mode") != "single":
            raise HTTPException(status_code=400, detail="Cannot set code on multi-file template")
        validation = validate_code(template_data.code)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid template code: {validation['error']}")
        update_fields["code"] = template_data.code

    # Handle files update (multi-file mode)
    if template_data.files is not None:
        if template.get("mode") != "multi":
            raise HTTPException(status_code=400, detail="Cannot set files on single-file template")
        validation = validate_multifile(
            template_data.files,
            template.get("entrypoint", "app.py"),
            template.get("framework", "fastapi")
        )
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid template code: {validation['error']}")
        update_fields["files"] = template_data.files

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    await templates_collection.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": update_fields}
    )

    # Fetch updated template
    updated = await templates_collection.find_one({"_id": ObjectId(template_id)})
    return template_to_response(updated)


@router.delete("/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    """Delete a user template"""
    try:
        template = await templates_collection.find_one({"_id": ObjectId(template_id)})
    except:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check ownership - cannot delete global templates or other users' templates
    if template.get("is_global"):
        raise HTTPException(status_code=403, detail="Cannot delete global templates")
    if str(template.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    await templates_collection.delete_one({"_id": ObjectId(template_id)})

    return {"success": True, "deleted_id": template_id}
