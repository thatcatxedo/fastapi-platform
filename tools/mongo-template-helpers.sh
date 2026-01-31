#!/bin/bash
# MongoDB Template Helper Commands
# Source this file: source tools/mongo-template-helpers.sh

NAMESPACE="${NAMESPACE:-fastapi-platform}"

# List all templates
tpl-list() {
  kubectl exec -n $NAMESPACE deployment/backend -- python3 -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
for t in db.templates.find({}, {'name':1,'mode':1,'framework':1,'is_global':1}).sort('name',1):
    scope = 'G' if t.get('is_global') else 'U'
    mode = t.get('mode','single')[:5]
    fw = (t.get('framework') or '-')[:8]
    print(f'[{scope}] {mode:5} {fw:8} {t[\"name\"]}')
"
}

# Get template by name
tpl-get() {
  local name="$1"
  kubectl exec -n $NAMESPACE deployment/backend -- python3 -c "
import json
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
t = db.templates.find_one({'name': '$name'})
if t:
    t['_id'] = str(t['_id'])
    print(json.dumps(t, indent=2, default=str))
else:
    print('Not found')
"
}

# Get just the files dict for a multi-file template
tpl-files() {
  local name="$1"
  kubectl exec -n $NAMESPACE deployment/backend -- python3 -c "
import json
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
t = db.templates.find_one({'name': '$name'}, {'files':1})
if t and t.get('files'):
    for fname in sorted(t['files'].keys()):
        print(f'=== {fname} ===')
        print(t['files'][fname])
        print()
else:
    print('Not found or no files')
"
}

# Update a specific file in a template
tpl-update-file() {
  local name="$1"
  local filename="$2"
  local code="$3"

  # Escape the code for Python
  escaped_code=$(echo "$code" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

  kubectl exec -n $NAMESPACE deployment/backend -- python3 -c "
import json
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
code = $escaped_code
result = db.templates.update_one(
    {'name': '$name'},
    {'\$set': {'files.$filename': code}}
)
print(f'Modified: {result.modified_count}')
"
}

# Create a simple single-file template
tpl-create-single() {
  local name="$1"
  local desc="$2"
  local code="$3"
  local complexity="${4:-simple}"
  local tags="${5:-}"

  escaped_code=$(echo "$code" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

  kubectl exec -n $NAMESPACE deployment/backend -- python3 -c "
import json
from pymongo import MongoClient
from datetime import datetime
import os
client = MongoClient(os.environ['MONGO_URI'])
db = client.get_default_database()
code = $escaped_code
tags = '$tags'.split(',') if '$tags' else []
doc = {
    'name': '$name',
    'description': '$desc',
    'code': code,
    'mode': 'single',
    'is_global': True,
    'complexity': '$complexity',
    'tags': tags,
    'created_at': datetime.utcnow()
}
result = db.templates.insert_one(doc)
print(f'Created: {result.inserted_id}')
"
}

echo "Template helpers loaded. Commands: tpl-list, tpl-get, tpl-files, tpl-update-file, tpl-create-single"
