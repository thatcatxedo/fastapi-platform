# Template System

This document explains how templates are stored and managed in the platform.

## Overview

Templates are stored in two places:
1. **Global templates**: YAML files in `backend/templates/global/` - seeded on startup
2. **User templates**: MongoDB `templates` collection with `is_global: false`

## Global Templates (YAML Files)

Global templates are stored as individual YAML files in `backend/templates/global/`:

```
backend/templates/global/
├── hello_world_api.yaml
├── todo_api.yaml
├── fasthtml_starter.yaml
├── fullstack_notes_app.yaml
├── slack_bot.yaml
├── fastapi_multifile_starter.yaml
├── fasthtml_multifile_starter.yaml
└── weather_tracker.yaml
```

### YAML Format

**Single-file template:**
```yaml
name: "Hello World API"
description: "A simple FastAPI app with basic routing..."
complexity: simple
tags: [beginner, routing, basics]
mode: single
code: |
  from fastapi import FastAPI
  app = FastAPI()

  @app.get("/")
  async def root():
      return {"message": "Hello World"}
```

**Multi-file template:**
```yaml
name: "FastAPI Multi-File Starter"
description: "An organized FastAPI app..."
complexity: medium
tags: [multifile, fastapi, mongodb]
mode: multi
framework: fastapi
entrypoint: app.py
files:
  app.py: |
    from fastapi import FastAPI
    ...
  routes.py: |
    from fastapi import APIRouter
    ...
```

### Template Loading

On backend startup, `seed_templates.py` calls `load_global_templates()` from `templates/loader.py`:
1. Reads all `.yaml` files from `templates/global/`
2. Validates each template with Pydantic (`TemplateData` model)
3. Upserts into MongoDB (creates or updates based on name)

Templates are validated for:
- Required fields: `name`, `description`, `complexity`, `tags`
- Valid complexity: `simple`, `medium`, `complex`
- Mode-specific requirements: `code` for single-file, `files` dict for multi-file

## User Templates

Users can save their own templates via the "Save as Template" button in the editor.

### API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/templates` | List all templates (global + user's own) |
| POST | `/api/templates` | Create user template |
| PUT | `/api/templates/{id}` | Update own template |
| DELETE | `/api/templates/{id}` | Delete own template |

### Database Structure

```python
{
    "name": str,              # Template name (unique per user)
    "description": str,       # Template description
    "code": str,              # Code for single-file templates
    "files": dict,            # Files dict for multi-file templates
    "mode": str,              # "single" or "multi"
    "framework": str,         # "fastapi" or "fasthtml" (multi-file only)
    "entrypoint": str,        # Entry file (multi-file only)
    "complexity": str,        # "simple", "medium", or "complex"
    "tags": List[str],        # Tags for categorization
    "is_global": bool,        # True for system templates
    "user_id": str,           # User ID (None for global)
    "created_at": datetime    # Creation timestamp
}
```

### Access Control

- Users can only edit/delete templates where `is_global=False` AND `user_id=current_user._id`
- Template code is validated before save (same rules as app deployment)
- Unique index on `(user_id, name)` prevents duplicate names per user

## Troubleshooting

### Templates Missing After Startup

Check backend logs for seeding errors:
```bash
kubectl logs -n fastapi-platform deployment/backend | grep -i template
```

The `/health` endpoint reports template count - verify it shows 8+ templates.

### Adding New Global Templates

1. Create a new YAML file in `backend/templates/global/`
2. Follow the format above (single-file or multi-file)
3. Restart the backend - template will be seeded automatically

### Modifying Global Templates

Edit the YAML file and restart the backend. The upsert operation will update the existing template.
