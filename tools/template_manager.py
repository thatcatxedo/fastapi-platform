#!/usr/bin/env python3
"""
Template Manager - Direct MongoDB template management tool
Usage via kubectl exec:
  kubectl exec -n fastapi-platform deployment/backend -- python3 /tools/template_manager.py <command> [args]

Commands:
  list                          - List all templates
  get <name>                    - Get template details
  create <json>                 - Create template from JSON
  update <name> <json>          - Update template fields
  update-file <name> <file> <code> - Update a single file in multi-file template
  delete <name>                 - Delete a template (user templates only)
"""
import sys
import os
import json
from datetime import datetime

# Add app to path for imports
sys.path.insert(0, '/app')

from pymongo import MongoClient
from bson import ObjectId

client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))
db = client.get_default_database()
templates = db.templates


def list_templates():
    """List all templates with basic info"""
    results = templates.find({}, {
        'name': 1, 'mode': 1, 'framework': 1, 'is_global': 1,
        'complexity': 1, 'description': 1
    }).sort('name', 1)

    for t in results:
        scope = "GLOBAL" if t.get('is_global') else "USER"
        mode = t.get('mode', 'single')
        framework = t.get('framework', '-')
        complexity = t.get('complexity', '-')
        print(f"[{scope}] {t['name']}")
        print(f"    mode: {mode}, framework: {framework}, complexity: {complexity}")
        print(f"    {t.get('description', '')[:80]}...")
        print()


def get_template(name):
    """Get full template details"""
    t = templates.find_one({'name': name})
    if not t:
        print(f"Template '{name}' not found")
        return

    t['_id'] = str(t['_id'])
    print(json.dumps(t, indent=2, default=str))


def create_template(json_data):
    """Create a new template from JSON"""
    data = json.loads(json_data)

    # Validate required fields
    required = ['name', 'description']
    for field in required:
        if field not in data:
            print(f"Missing required field: {field}")
            return

    # Set defaults
    data.setdefault('is_global', True)
    data.setdefault('mode', 'single')
    data.setdefault('complexity', 'medium')
    data.setdefault('tags', [])
    data.setdefault('created_at', datetime.utcnow())

    # Validate mode-specific fields
    if data['mode'] == 'multi':
        if 'files' not in data:
            print("Multi-file templates require 'files' dict")
            return
        data.setdefault('entrypoint', 'app.py')
        data['code'] = None
    else:
        if 'code' not in data:
            print("Single-file templates require 'code'")
            return
        data['files'] = None

    # Check for duplicate
    if templates.find_one({'name': data['name'], 'is_global': data['is_global']}):
        print(f"Template '{data['name']}' already exists")
        return

    result = templates.insert_one(data)
    print(f"Created template '{data['name']}' with ID: {result.inserted_id}")


def update_template(name, json_data):
    """Update template fields"""
    data = json.loads(json_data)

    t = templates.find_one({'name': name})
    if not t:
        print(f"Template '{name}' not found")
        return

    # Don't allow changing certain fields
    data.pop('_id', None)
    data.pop('created_at', None)

    result = templates.update_one({'_id': t['_id']}, {'$set': data})
    if result.modified_count:
        print(f"Updated template '{name}'")
    else:
        print(f"No changes made to '{name}'")


def update_file(name, filename, code):
    """Update a single file in a multi-file template"""
    t = templates.find_one({'name': name})
    if not t:
        print(f"Template '{name}' not found")
        return

    if t.get('mode') != 'multi':
        print(f"Template '{name}' is not multi-file")
        return

    files = t.get('files', {})
    files[filename] = code

    result = templates.update_one(
        {'_id': t['_id']},
        {'$set': {'files': files}}
    )
    if result.modified_count:
        print(f"Updated file '{filename}' in template '{name}'")
    else:
        print(f"No changes made")


def delete_template(name):
    """Delete a user template (not global)"""
    t = templates.find_one({'name': name})
    if not t:
        print(f"Template '{name}' not found")
        return

    if t.get('is_global'):
        print(f"Cannot delete global template '{name}'. Set is_global=false first.")
        return

    templates.delete_one({'_id': t['_id']})
    print(f"Deleted template '{name}'")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'list':
        list_templates()
    elif cmd == 'get' and len(sys.argv) >= 3:
        get_template(sys.argv[2])
    elif cmd == 'create' and len(sys.argv) >= 3:
        create_template(sys.argv[2])
    elif cmd == 'update' and len(sys.argv) >= 4:
        update_template(sys.argv[2], sys.argv[3])
    elif cmd == 'update-file' and len(sys.argv) >= 5:
        update_file(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'delete' and len(sys.argv) >= 3:
        delete_template(sys.argv[2])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
