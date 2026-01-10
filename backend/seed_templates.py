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

async def seed_templates():
    """Seed templates collection with initial templates"""
    client = AsyncIOMotorClient(MONGO_URI)
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
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_templates())
