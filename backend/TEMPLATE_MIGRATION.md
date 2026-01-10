# Template Migration Guide

This document explains how templates are persisted in the database and how to manage them.

## Overview

Templates are stored in MongoDB and are automatically seeded on backend startup. The seeding process uses **upsert** operations, which means templates will be:
- Created if they don't exist
- Updated if they already exist (ensuring they're always up-to-date)
- Restored if they were accidentally deleted

## Automatic Seeding

Templates are automatically seeded when the backend starts up via the `lifespan` function in `main.py`. This ensures templates are always present.

## Manual Migration

If you need to manually migrate/restore templates, you can run:

```bash
cd backend
python migrate_templates.py
```

Or with a custom MongoDB URI:

```bash
MONGO_URI="mongodb://your-connection-string" python migrate_templates.py
```

## Template Persistence Features

1. **Upsert Operations**: Templates use MongoDB upsert, so they're always restored even if deleted
2. **Unique Index**: A unique index on `name + is_global` prevents duplicate global templates
3. **Automatic Updates**: Templates are updated on every startup to ensure they match the code
4. **Health Check**: The `/health` endpoint reports template count

## Current Templates

- **Hello World API**: Simple FastAPI app with basic routing
- **TODO API**: Full CRUD API with interactive HTML UI

## Database Structure

Templates are stored in the `templates` collection with the following structure:

```python
{
    "name": str,              # Template name (unique for global templates)
    "description": str,       # Template description
    "code": str,              # FastAPI code
    "complexity": str,        # "simple" or "medium"
    "is_global": bool,        # True for system templates
    "user_id": None,          # None for global templates
    "created_at": datetime,   # Creation timestamp
    "tags": List[str]        # Tags for categorization
}
```

## Troubleshooting

### Templates Missing

If templates are missing, check:

1. **Health Check**: `GET /health` - should show `templates: 2` or more
2. **Manual Migration**: Run `python migrate_templates.py`
3. **Backend Logs**: Check startup logs for seeding errors
4. **Database Connection**: Verify MongoDB connection is working

### Templates Overwritten

Templates are automatically restored on backend restart. The seeding function updates existing templates to match the code definition.

### Database Reset

If the database is reset, templates will be automatically restored on the next backend startup.
