#!/usr/bin/env python3
"""
Entrypoint for FastAPI runner container
Reads user code from ConfigMap and executes it safely
"""
import os
import sys
import importlib.util
from pathlib import Path

CODE_PATH = os.getenv("CODE_PATH", "/app/user_code.py")

def load_user_code():
    """Load and validate user code"""
    if not os.path.exists(CODE_PATH):
        print(f"Error: Code file not found at {CODE_PATH}", file=sys.stderr)
        sys.exit(1)
    
    with open(CODE_PATH, 'r') as f:
        code = f.read()
    
    # Basic validation
    if 'app = FastAPI()' not in code:
        print("Error: Code must define 'app = FastAPI()'", file=sys.stderr)
        sys.exit(1)
    
    return code

def execute_code(code: str):
    """Execute user code in isolated namespace"""
    # Create a clean namespace for execution
    user_globals = {
        '__builtins__': __builtins__,
        '__name__': '__main__',
        '__file__': CODE_PATH,
    }
    
    # Import FastAPI and Pydantic into user namespace
    from fastapi import FastAPI
    from pydantic import BaseModel
    from typing import Optional, List, Dict, Any
    from datetime import datetime
    
    user_globals.update({
        'FastAPI': FastAPI,
        'BaseModel': BaseModel,
        'Optional': Optional,
        'List': List,
        'Dict': Dict,
        'Any': Any,
        'datetime': datetime,
    })
    
    try:
        exec(compile(code, CODE_PATH, 'exec'), user_globals)
    except Exception as e:
        print(f"Error executing user code: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get the app instance
    if 'app' not in user_globals:
        print("Error: Code must define 'app = FastAPI()'", file=sys.stderr)
        sys.exit(1)
    
    return user_globals['app']

def main():
    print(f"Loading user code from {CODE_PATH}...")
    code = load_user_code()
    
    print("Executing user code...")
    app = execute_code(code)
    
    # Add health endpoint if not present
    if not any(route.path == "/health" for route in app.routes):
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
    
    # Patch Swagger UI to use correct path for OpenAPI schema
    # Since Traefik strips the path prefix, /openapi.json works, but we need to ensure
    # Swagger UI loads it correctly. The issue is Swagger UI uses absolute paths.
    # We'll replace it with the same absolute path since the middleware handles routing.
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import HTMLResponse
    
    class SwaggerUIPatchMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if request.url.path == "/docs" and isinstance(response, HTMLResponse):
                # Get HTML content
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                html = body.decode('utf-8')
                # The path /openapi.json should work after Traefik strips prefix
                # But Swagger UI might need the full path. Let's try keeping it absolute
                # since the middleware will route it correctly
                # Actually, let's use a relative path that works: just 'openapi.json'
                html = html.replace("url: '/openapi.json'", "url: 'openapi.json'")
                html = html.replace('url: "/openapi.json"', 'url: "openapi.json"')
                return HTMLResponse(content=html, status_code=response.status_code)
            return response
    
    app.add_middleware(SwaggerUIPatchMiddleware)
    
    print("Starting uvicorn server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
