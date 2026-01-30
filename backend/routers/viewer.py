"""
MongoDB viewer routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging

from models import ViewerResponse
from auth import get_current_user, generate_viewer_password, hash_password
from database import viewer_instances_collection
from utils import error_payload
from config import APP_DOMAIN
from deployment import create_mongo_viewer_resources, get_mongo_viewer_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/viewer", tags=["viewer"])


def build_viewer_response(
    url: str,
    username: str,
    password: str = None,
    password_provided: bool = False,
    status_info: dict = None
) -> ViewerResponse:
    """Build a ViewerResponse from viewer data."""
    return ViewerResponse(
        url=url,
        username=username,
        password=password,
        password_provided=password_provided,
        ready=status_info["ready"] if status_info else False,
        pod_status=status_info["pod_status"] if status_info else None
    )


@router.post("", response_model=ViewerResponse)
async def provision_viewer(user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    viewer = await viewer_instances_collection.find_one({"user_id": user["_id"]})

    # Always compute current URL format (in case routing scheme changed)
    current_url = f"https://mongo-{user_id}.{APP_DOMAIN}"

    if viewer:
        status_info = await get_mongo_viewer_status(user_id)

        # If URL format changed, update the IngressRoute and DB
        if viewer.get("url") != current_url:
            try:
                await create_mongo_viewer_resources(user_id, user, viewer["username"], "")
            except Exception as e:
                logger.warning(f"Failed to update viewer resources: {e}")
            await viewer_instances_collection.update_one(
                {"_id": viewer["_id"]},
                {"$set": {"last_access": datetime.utcnow(), "url": current_url}}
            )
        else:
            await viewer_instances_collection.update_one(
                {"_id": viewer["_id"]},
                {"$set": {"last_access": datetime.utcnow()}}
            )

        return build_viewer_response(current_url, viewer["username"], status_info=status_info)

    username = f"user_{user_id}"
    password = generate_viewer_password()
    url = f"https://mongo-{user_id}.{APP_DOMAIN}"

    try:
        await create_mongo_viewer_resources(user_id, user, username, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_payload("VIEWER_CREATE_FAILED", str(e)))

    status_info = await get_mongo_viewer_status(user_id)

    await viewer_instances_collection.insert_one({
        "user_id": user["_id"],
        "username": username,
        "password_hash": hash_password(password),
        "url": url,
        "created_at": datetime.utcnow(),
        "last_access": datetime.utcnow()
    })

    return build_viewer_response(url, username, password, password_provided=True, status_info=status_info)


@router.post("/rotate", response_model=ViewerResponse)
async def rotate_viewer_credentials(user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    viewer = await viewer_instances_collection.find_one({"user_id": user["_id"]})

    username = viewer["username"] if viewer else f"user_{user_id}"
    password = generate_viewer_password()
    url = f"https://mongo-{user_id}.{APP_DOMAIN}"

    try:
        await create_mongo_viewer_resources(user_id, user, username, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=error_payload("VIEWER_ROTATE_FAILED", str(e)))

    status_info = await get_mongo_viewer_status(user_id)

    update_doc = {
        "username": username,
        "password_hash": hash_password(password),
        "url": url,
        "last_access": datetime.utcnow()
    }

    if viewer:
        await viewer_instances_collection.update_one(
            {"_id": viewer["_id"]},
            {"$set": update_doc}
        )
    else:
        update_doc["user_id"] = user["_id"]
        update_doc["created_at"] = datetime.utcnow()
        await viewer_instances_collection.insert_one(update_doc)

    return build_viewer_response(url, username, password, password_provided=True, status_info=status_info)
