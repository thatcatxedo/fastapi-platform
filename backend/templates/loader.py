"""
YAML template loader for FastAPI Platform.

Loads template definitions from YAML files in the global/ directory.
"""
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, validator

logger = logging.getLogger("uvicorn")

TEMPLATES_DIR = Path(__file__).parent / "global"


class TemplateData(BaseModel):
    """Validated template data from YAML files."""
    name: str
    description: str
    complexity: str
    tags: List[str]
    mode: str = "single"
    # Single-file templates
    code: Optional[str] = None
    # Multi-file templates
    framework: Optional[str] = None
    entrypoint: Optional[str] = None
    files: Optional[Dict[str, str]] = None

    @validator("complexity")
    def validate_complexity(cls, v):
        if v not in ("simple", "medium", "complex"):
            raise ValueError(f"complexity must be one of: simple, medium, complex")
        return v

    @validator("mode")
    def validate_mode(cls, v):
        if v not in ("single", "multi"):
            raise ValueError(f"mode must be one of: single, multi")
        return v

    @validator("code", always=True)
    def validate_code_for_single(cls, v, values):
        if values.get("mode") == "single" and not v:
            raise ValueError("single-file templates must have code")
        return v

    @validator("files", always=True)
    def validate_files_for_multi(cls, v, values):
        if values.get("mode") == "multi" and not v:
            raise ValueError("multi-file templates must have files")
        return v


def load_template_from_yaml(yaml_path: Path) -> Optional[TemplateData]:
    """Load and validate a single template from a YAML file."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        template = TemplateData(**data)
        return template
    except Exception as e:
        logger.error(f"Failed to load template from {yaml_path.name}: {e}")
        return None


def load_global_templates(templates_dir: Path = TEMPLATES_DIR) -> List[Dict[str, Any]]:
    """
    Load all global templates from YAML files.

    Returns a list of template dictionaries ready for MongoDB upsert.
    """
    templates = []

    if not templates_dir.exists():
        logger.warning(f"Templates directory not found: {templates_dir}")
        return templates

    yaml_files = sorted(templates_dir.glob("*.yaml"))

    if not yaml_files:
        logger.warning(f"No YAML template files found in {templates_dir}")
        return templates

    for yaml_file in yaml_files:
        template_data = load_template_from_yaml(yaml_file)
        if template_data:
            # Convert to dict for MongoDB
            template_dict = {
                "name": template_data.name,
                "description": template_data.description,
                "complexity": template_data.complexity,
                "tags": template_data.tags,
                "mode": template_data.mode,
                "is_global": True,
                "user_id": None,
            }

            # Add mode-specific fields
            if template_data.mode == "single":
                template_dict["code"] = template_data.code
                template_dict["files"] = None
                template_dict["framework"] = None
                template_dict["entrypoint"] = None
            else:
                template_dict["code"] = None
                template_dict["files"] = template_data.files
                template_dict["framework"] = template_data.framework
                template_dict["entrypoint"] = template_data.entrypoint

            templates.append(template_dict)
            logger.debug(f"Loaded template: {template_data.name}")

    logger.info(f"Loaded {len(templates)} global templates from YAML files")
    return templates
