#!/usr/bin/env python3
"""
Seed script to populate templates collection with initial templates
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId

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
    return """<!DOCTYPE html>
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
</html>"""

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

async def seed_templates(client=None):
    """Seed templates collection with initial templates"""
    close_client = False
    if client is None:
        client = AsyncIOMotorClient(MONGO_URI)
        close_client = True
    
    db = client.fastapi_platform_db
    templates_collection = db.templates
    
    templates_to_seed = [SIMPLE_TEMPLATE, MEDIUM_TEMPLATE]
    
    for template in templates_to_seed:
        # Check if template already exists (by name and is_global)
        existing = await templates_collection.find_one({
            "name": template["name"],
            "is_global": True
        })
        
        if existing:
            print(f"Template '{template['name']}' already exists, skipping...")
        else:
            result = await templates_collection.insert_one(template)
            print(f"✓ Seeded template: {template['name']} (ID: {result.inserted_id})")
    
    print("\nTemplate seeding complete!")
    
    if close_client:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_templates())
