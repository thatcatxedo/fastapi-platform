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
    
    # Ensure docs are enabled (FastAPI enables them by default, but ensure they're accessible)
    # FastAPI automatically creates /docs, /redoc, and /openapi.json endpoints
    # We just need to make sure they're not disabled
    if app.docs_url is None:
        app.docs_url = "/docs"
    if app.redoc_url is None:
        app.redoc_url = "/redoc"
    if app.openapi_url is None:
        app.openapi_url = "/openapi.json"
    
    # Add health endpoint if not present
    if not any(route.path == "/health" for route in app.routes):
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
    
    # Patch Swagger UI to use correct path for OpenAPI schema
    # Since Traefik strips the path prefix, we need Swagger UI to load openapi.json
    # relative to the current path, not from root
    from starlette.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import HTMLResponse
    from starlette.responses import Response
    
    class SwaggerUIPatchMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            # Check if this is the /docs endpoint
            if request.url.path == "/docs":
                # Read the response body
                body = b""
                if hasattr(response, 'body_iterator'):
                    async for chunk in response.body_iterator:
                        body += chunk
                elif hasattr(response, 'body'):
                    body = response.body
                
                # Check if it's HTML (Swagger UI)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type or body.startswith(b'<!'):
                    html = body.decode('utf-8')
                    # Replace absolute /openapi.json with relative openapi.json
                    # This ensures it loads from the same path as /docs
                    html = html.replace("url: '/openapi.json'", "url: 'openapi.json'")
                    html = html.replace('url: "/openapi.json"', 'url: "openapi.json"')
                    return HTMLResponse(content=html, status_code=response.status_code, headers=dict(response.headers))
            return response
    
    app.add_middleware(SwaggerUIPatchMiddleware)
    
    print("Starting uvicorn server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
