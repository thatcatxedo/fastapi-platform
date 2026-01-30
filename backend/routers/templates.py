"""
Template routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from bson import ObjectId

from models import TemplateResponse
from auth import get_current_user
from database import templates_collection

router = APIRouter(prefix="/api/templates", tags=["templates"])


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
    return [
        TemplateResponse(
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
            created_at=t["created_at"].isoformat() if isinstance(t.get("created_at"), datetime) else t.get("created_at", "")
        )
        for t in all_templates
    ]


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
    
    return TemplateResponse(
        id=str(template["_id"]),
        name=template["name"],
        description=template["description"],
        code=template.get("code"),
        mode=template.get("mode", "single"),
        framework=template.get("framework"),
        entrypoint=template.get("entrypoint"),
        files=template.get("files"),
        complexity=template["complexity"],
        is_global=template["is_global"],
        created_at=template["created_at"].isoformat() if isinstance(template.get("created_at"), datetime) else template.get("created_at", "")
    )
