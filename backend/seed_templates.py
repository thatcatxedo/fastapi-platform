#!/usr/bin/env python3
"""
Seed script to populate templates collection with initial templates
"""
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger("uvicorn")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

SIMPLE_TEMPLATE = {
    "name": "Hello World API",
    "description": "A simple FastAPI app with basic routing, path parameters, and request bodies. Perfect for learning the fundamentals.",
    "code": """from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/hello/{name}")
async def hello(name: str):
    return {"message": f"Hello, {name}!"}

class Greeting(BaseModel):
    name: str
    message: str

@app.post("/greet")
async def greet(greeting: Greeting):
    return {"greeting": f"{greeting.message}, {greeting.name}!"}
""",
    "complexity": "simple",
    "is_global": True,
    "user_id": None,
    "created_at": datetime.utcnow(),
    "tags": ["beginner", "routing", "basics"]
}

MEDIUM_TEMPLATE = {
    "name": "TODO API",
    "description": "A full CRUD API with Pydantic models, in-memory storage, and error handling. Learn how to build REST APIs with FastAPI.",
    "code": """from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# In-memory storage
todos = []
next_id = 1

class Todo(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TodoResponse(Todo):
    id: int
    created_at: datetime

@app.get("/", response_class=HTMLResponse)
async def root():
    return \"\"\"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TODO API - Interactive UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
            cursor: pointer;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button.secondary {
            background: #6c757d;
        }
        button.danger {
            background: #dc3545;
        }
        .todos-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .todo-item {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
        }
        .todo-item.completed {
            opacity: 0.7;
            border-left-color: #28a745;
        }
        .todo-item h3 {
            color: #333;
            margin-bottom: 5px;
        }
        .todo-item.completed h3 {
            text-decoration: line-through;
        }
        .todo-item p {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .todo-item .meta {
            font-size: 12px;
            color: #999;
            margin-bottom: 10px;
        }
        .todo-item .actions {
            display: flex;
            gap: 10px;
        }
        .todo-item .actions button {
            padding: 6px 12px;
            font-size: 12px;
        }
        .curl-examples {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin-top: 15px;
        }
        .curl-examples h3 {
            color: #4ec9b0;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .curl-examples pre {
            margin-bottom: 15px;
            padding: 10px;
            background: #252526;
            border-radius: 4px;
            border-left: 3px solid #007acc;
        }
        .curl-examples code {
            color: #ce9178;
        }
        .response-area {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .response-area pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 TODO API</h1>
            <p>Interactive UI with CRUD Operations</p>
        </div>
        
        <div class="main-content">
            <div class="card">
                <h2>Create Todo</h2>
                <form id="todoForm">
                    <div class="form-group">
                        <label for="title">Title *</label>
                        <input type="text" id="title" required placeholder="Enter todo title">
                    </div>
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" placeholder="Enter todo description (optional)"></textarea>
                    </div>
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="completed">
                            <label for="completed">Completed</label>
                        </div>
                    </div>
                    <button type="submit">Create Todo</button>
                    <button type="button" class="secondary" onclick="loadTodos()">Refresh List</button>
                </form>
                
                <div class="response-area" id="response"></div>
            </div>
            
            <div class="card">
                <h2>Todos List</h2>
                <div id="todosList" class="todos-list">
                    <p style="color: #999; text-align: center;">No todos yet. Create one to get started!</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 cURL Examples</h2>
            <div class="curl-examples">
                <h3>GET all todos</h3>
                <pre><code>curl -X GET "http://localhost:8000/todos"</code></pre>
                
                <h3>GET a specific todo</h3>
                <pre><code>curl -X GET "http://localhost:8000/todos/1"</code></pre>
                
                <h3>CREATE a todo</h3>
                <pre><code>curl -X POST "http://localhost:8000/todos" \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Buy groceries", "description": "Milk, eggs, bread", "completed": false}'</code></pre>
                
                <h3>UPDATE a todo</h3>
                <pre><code>curl -X PUT "http://localhost:8000/todos/1" \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Buy groceries", "description": "Milk, eggs, bread", "completed": true}'</code></pre>
                
                <h3>DELETE a todo</h3>
                <pre><code>curl -X DELETE "http://localhost:8000/todos/1"</code></pre>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = window.location.origin;
        
        async function loadTodos() {
            try {
                const response = await fetch(`${API_BASE}/todos`);
                const todos = await response.json();
                displayTodos(todos);
            } catch (error) {
                showResponse('Error loading todos: ' + error.message);
            }
        }
        
        function displayTodos(todos) {
            const listDiv = document.getElementById('todosList');
            if (todos.length === 0) {
                listDiv.innerHTML = '<p style="color: #999; text-align: center;">No todos yet. Create one to get started!</p>';
                return;
            }
            
            listDiv.innerHTML = todos.map(todo => `
                <div class="todo-item ${todo.completed ? 'completed' : ''}">
                    <h3>${escapeHtml(todo.title)}</h3>
                    ${todo.description ? `<p>${escapeHtml(todo.description)}</p>` : ''}
                    <div class="meta">ID: ${todo.id} | Created: ${new Date(todo.created_at).toLocaleString()}</div>
                    <div class="actions">
                        <button onclick="toggleTodo(${todo.id}, ${!todo.completed})">
                            ${todo.completed ? 'Mark Incomplete' : 'Mark Complete'}
                        </button>
                        <button class="danger" onclick="deleteTodo(${todo.id})">Delete</button>
                    </div>
                </div>
            `).join('');
        }
        
        async function toggleTodo(id, completed) {
            try {
                // First fetch the current todo
                const getResponse = await fetch(`${API_BASE}/todos/${id}`);
                if (!getResponse.ok) {
                    showResponse('Error fetching todo');
                    return;
                }
                const todo = await getResponse.json();
                
                // Then update it
                const response = await fetch(`${API_BASE}/todos/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: todo.title,
                        description: todo.description,
                        completed: completed
                    })
                });
                
                if (response.ok) {
                    loadTodos();
                    showResponse('Todo updated successfully!');
                } else {
                    showResponse('Error updating todo');
                }
            } catch (error) {
                showResponse('Error: ' + error.message);
            }
        }
        
        async function deleteTodo(id) {
            if (!confirm('Are you sure you want to delete this todo?')) return;
            
            try {
                const response = await fetch(`${API_BASE}/todos/${id}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    loadTodos();
                    showResponse('Todo deleted successfully!');
                } else {
                    showResponse('Error deleting todo');
                }
            } catch (error) {
                showResponse('Error: ' + error.message);
            }
        }
        
        document.getElementById('todoForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const title = document.getElementById('title').value;
            const description = document.getElementById('description').value;
            const completed = document.getElementById('completed').checked;
            
            try {
                const response = await fetch(`${API_BASE}/todos`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description, completed })
                });
                
                const data = await response.json();
                if (response.ok) {
                    showResponse('Todo created: ' + JSON.stringify(data, null, 2));
                    document.getElementById('todoForm').reset();
                    loadTodos();
                } else {
                    showResponse('Error: ' + JSON.stringify(data, null, 2));
                }
            } catch (error) {
                showResponse('Error: ' + error.message);
            }
        });
        
        function showResponse(message) {
            const responseDiv = document.getElementById('response');
            responseDiv.innerHTML = `<pre>${escapeHtml(message)}</pre>`;
            setTimeout(() => {
                responseDiv.innerHTML = '';
            }, 5000);
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Load todos on page load
        loadTodos();
    </script>
</body>
</html>\"\"\"

@app.get("/todos", response_model=List[TodoResponse])
async def get_todos():
    return todos

@app.post("/todos", response_model=TodoResponse)
async def create_todo(todo: Todo):
    global next_id
    new_todo = TodoResponse(
        id=next_id,
        **todo.dict(),
        created_at=datetime.utcnow()
    )
    todos.append(new_todo)
    next_id += 1
    return new_todo

@app.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int):
    todo = next((t for t in todos if t.id == todo_id), None)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@app.put("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, todo: Todo):
    index = next((i for i, t in enumerate(todos) if t.id == todo_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    todos[index] = TodoResponse(id=todo_id, **todo.dict(), created_at=todos[index].created_at)
    return todos[index]

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    global todos
    todos = [t for t in todos if t.id != todo_id]
    return {"message": "Todo deleted"}
""",
    "complexity": "medium",
    "is_global": True,
    "user_id": None,
    "created_at": datetime.utcnow(),
    "tags": ["crud", "rest", "models", "intermediate"]
}

FASTHTML_TEMPLATE = {
    "name": "FastHTML Starter",
    "description": "A minimal FastHTML app showing server-rendered UI with FastTags. Great for HTML-first workflows.",
    "code": """from fasthtml.common import *

# FastHTML app object and shortcut for routing
app, rt = fast_app()

@rt
def index():
    return Titled(
        "FastHTML Starter",
        P("This is a server-rendered HTML app built with FastHTML."),
        P("Edit this page and add routes to build your UI.")
    )
""",
    "complexity": "simple",
    "is_global": True,
    "user_id": None,
    "created_at": datetime.utcnow(),
    "tags": ["html", "fasthtml", "htmx", "starter"]
}

FULLSTACK_MONGO_TEMPLATE = {
    "name": "Full-Stack Notes App",
    "description": "A complete full-stack app with MongoDB persistence and server-rendered HTML.",
    "code": '''from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

app = FastAPI()

# Connect to platform-provided MongoDB
client = MongoClient(os.environ.get("PLATFORM_MONGO_URI", "mongodb://localhost:27017/test"))
db = client.get_default_database()
notes = db.notes

def render_page(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: system-ui, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        input, textarea {{ width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }}
        .note {{ border-left: 4px solid #667eea; }}
        .delete {{ background: #e53e3e; font-size: 12px; padding: 5px 10px; }}
    </style>
</head>
<body><div class="container">{content}</div></body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    all_notes = list(notes.find().sort("created_at", -1))
    notes_html = ""
    for note in all_notes:
        notes_html += f"""
        <div class="card note">
            <h3>{note['title']}</h3>
            <p>{note['content']}</p>
            <small>Created: {note['created_at'].strftime('%Y-%m-%d %H:%M')}</small>
            <form action="delete/{note['_id']}" method="post" style="display:inline; margin-left:10px;">
                <button type="submit" class="delete">Delete</button>
            </form>
        </div>"""
    if not notes_html:
        notes_html = '<p style="color:#999;text-align:center;">No notes yet.</p>'

    content = f"""
        <h1>My Notes</h1>
        <div class="card">
            <form action="create" method="post">
                <input name="title" placeholder="Note title" required>
                <textarea name="content" placeholder="Note content" rows="3" required></textarea>
                <button type="submit">Add Note</button>
            </form>
        </div>
        {notes_html}
        <p style="margin-top:20px;color:#666;">Data persists in your database. <a href="api/notes">JSON API</a></p>
    """
    return render_page("My Notes", content)

@app.post("/create")
async def create_note(title: str = Form(...), content: str = Form(...)):
    notes.insert_one({"title": title, "content": content, "created_at": datetime.utcnow()})
    return RedirectResponse(url="./", status_code=303)

@app.post("/delete/{note_id}")
async def delete_note(note_id: str):
    notes.delete_one({"_id": ObjectId(note_id)})
    return RedirectResponse(url="../", status_code=303)

@app.get("/api/notes")
async def api_list_notes():
    return [{"id": str(n["_id"]), "title": n["title"], "content": n["content"]} for n in notes.find()]
''',
    "complexity": "medium",
    "is_global": True,
    "user_id": None,
    "created_at": datetime.utcnow(),
    "tags": ["fullstack", "mongodb", "crud", "html", "persistence"]
}

SLACK_BOT_TEMPLATE = {
    "name": "Hello World Slack Bot",
    "description": "A simple Slack bot that responds to mentions using the Slack Events API. Learn how to build Slack integrations with webhooks and event handling.",
    "code": '''from fastapi import FastAPI, Request, HTTPException, Header
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web import WebClient
import os
import json

app = FastAPI()

# Slack configuration - set these as environment variables in your app settings
# Get these from https://api.slack.com/apps -> Your App -> Basic Information
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# Initialize Slack signature verifier and web client
signature_verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

@app.get("/")
async def root():
    return {
        "message": "Slack Bot is running!",
        "instructions": "Configure SLACK_SIGNING_SECRET and SLACK_BOT_TOKEN environment variables, then set your Slack app's Event Subscriptions URL to: https://your-app-url/slack/events"
    }

@app.post("/slack/events")
async def slack_events(request: Request, x_slack_signature: str = Header(None), x_slack_request_timestamp: str = Header(None)):
    """
    Handle Slack Events API webhook.
    
    Setup instructions:
    1. Create a Slack app at https://api.slack.com/apps
    2. Go to "Event Subscriptions" and enable it
    3. Set Request URL to: https://your-app-url/slack/events
    4. Subscribe to "app_mentions" event (bot_events)
    5. Install app to workspace and get Bot User OAuth Token
    6. Copy Signing Secret from Basic Information
    7. Add both as environment variables: SLACK_SIGNING_SECRET and SLACK_BOT_TOKEN
    """
    body = await request.body()
    
    # Verify request signature
    if not signature_verifier.is_valid(
        body=body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    data = await request.json()
    
    # Handle URL verification challenge (Slack sends this when you first add the URL)
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Handle events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        event_type = event.get("type")
        
        # Respond to app_mention events (when someone mentions your bot)
        if event_type == "app_mention":
            channel = event.get("channel")
            text = event.get("text", "")
            user = event.get("user")
            
            # Simple response
            if slack_client:
                try:
                    slack_client.chat_postMessage(
                        channel=channel,
                        text="Hello World! 👋 You mentioned me!"
                    )
                except Exception as e:
                    print(f"Error posting message: {e}")
            
            return {"status": "ok"}
    
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
    "complexity": "simple",
    "is_global": True,
    "user_id": None,
    "created_at": datetime.utcnow(),
    "tags": ["slack", "bot", "webhook", "events-api"]
}

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
        logger.info("✓ Template indexes ensured")
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
    
    templates_to_seed = [SIMPLE_TEMPLATE, MEDIUM_TEMPLATE, FASTHTML_TEMPLATE, FULLSTACK_MONGO_TEMPLATE, SLACK_BOT_TEMPLATE]
    
    for template in templates_to_seed:
        # Use upsert (replace or insert) to ensure template is always present
        # This makes templates persistent - they'll be restored even if deleted
        filter_query = {
            "name": template["name"],
            "is_global": True
        }
        
        # Prepare update document - preserve _id if exists, update everything else
        update_doc = {
            "$set": {
                "description": template["description"],
                "code": template["code"],
                "complexity": template["complexity"],
                "tags": template["tags"],
                "is_global": template["is_global"],
                "user_id": template["user_id"]
            },
            "$setOnInsert": {
                "created_at": template["created_at"]
            }
        }
        
        result = await templates_collection.update_one(
            filter_query,
            update_doc,
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"✓ Created template: {template['name']} (ID: {result.upserted_id})")
        elif result.modified_count > 0:
            logger.info(f"✓ Updated template: {template['name']}")
        else:
            logger.debug(f"Template '{template['name']}' already exists and is up-to-date")
    
    logger.info("Template seeding complete!")
    
    if close_client:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_templates())
