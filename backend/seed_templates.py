#!/usr/bin/env python3
"""
Seed script to populate templates collection with initial templates.

Templates are loaded from YAML files in templates/global/ directory.
"""
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

from templates import load_global_templates

logger = logging.getLogger("uvicorn")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


async def ensure_indexes(templates_collection):
    """Ensure unique index on template name + is_global to prevent duplicates"""
    try:
        # Create unique index on name + is_global for global templates
        # This ensures we can't have duplicate global templates
        await templates_collection.create_index(
            [("name", 1), ("is_global", 1)],
            unique=True,
            partialFilterExpression={"is_global": True}
        )
        logger.info("Template indexes ensured")
    except Exception as e:
        # Index might already exist, that's fine
        logger.debug(f"Index creation note: {e}")


async def seed_templates(client=None, force_update=False):
    """
    Seed templates collection with initial templates.
    Uses upsert to ensure templates are always present and up-to-date.

    Args:
        client: Optional MongoDB client (creates new one if None)
        force_update: If True, always update templates even if they exist
    """
    close_client = False
    if client is None:
        client = AsyncIOMotorClient(MONGO_URI)
        close_client = True

    db = client.fastapi_platform_db
    templates_collection = db.templates

    # Ensure indexes for data integrity
    await ensure_indexes(templates_collection)

    # Load templates from YAML files
    templates_to_seed = load_global_templates()

    if not templates_to_seed:
        logger.warning("No templates loaded from YAML files!")
        if close_client:
            client.close()
        return

    for template in templates_to_seed:
        # Use upsert (replace or insert) to ensure template is always present
        # This makes templates persistent - they'll be restored even if deleted
        filter_query = {
            "name": template["name"],
            "is_global": True
        }

        # Prepare update document - preserve _id if exists, update everything else
        set_fields = {
            "description": template["description"],
            "complexity": template["complexity"],
            "tags": template["tags"],
            "is_global": template["is_global"],
            "user_id": template["user_id"],
            "mode": template.get("mode", "single"),
            "code": template.get("code"),
            "files": template.get("files"),
            "framework": template.get("framework"),
            "entrypoint": template.get("entrypoint"),
            "requires_database": template.get("requires_database", False),
        }

        update_doc = {
            "$set": set_fields,
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "is_hidden": False,
            }
        }

        result = await templates_collection.update_one(
            filter_query,
            update_doc,
            upsert=True
        )

        if result.upserted_id:
            logger.info(f"Created template: {template['name']} (ID: {result.upserted_id})")
        elif result.modified_count > 0:
            logger.info(f"Updated template: {template['name']}")
        else:
            logger.debug(f"Template '{template['name']}' already exists and is up-to-date")

    logger.info(f"Template seeding complete! ({len(templates_to_seed)} templates)")

    if close_client:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_templates())
