#!/usr/bin/env python3
"""
Migration script to ensure templates are persisted in the database.
Can be run independently or as part of deployment/init process.

Usage:
    python migrate_templates.py
    # Or with custom MONGO_URI:
    MONGO_URI="mongodb://..." python migrate_templates.py
"""
import os
import sys
import asyncio
import logging
from seed_templates import seed_templates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run template migration"""
    logger.info("Starting template migration...")
    try:
        await seed_templates(force_update=True)
        logger.info("✓ Template migration completed successfully")
        return 0
    except Exception as e:
        logger.error(f"✗ Template migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
