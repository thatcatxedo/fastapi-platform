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
    if 'app = FastAPI()' not in code and 'fast_app(' not in code and 'FastHTML(' not in code:
        print("Error: Code must define an app instance (FastAPI or FastHTML)", file=sys.stderr)
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
        print("Error: Code must define an app instance", file=sys.stderr)
        sys.exit(1)
    
    return user_globals['app']

def add_health_wrapper(app):
    async def wrapped(scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/health":
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"status":"healthy"}',
            })
            return
        await app(scope, receive, send)

    return wrapped

def main():
    print(f"Loading user code from {CODE_PATH}...")
    code = load_user_code()
    
    print("Executing user code...")
    app = execute_code(code)
    
    if hasattr(app, "docs_url") and hasattr(app, "add_middleware"):
        if app.docs_url is None:
            app.docs_url = "/docs"
        if getattr(app, "redoc_url", None) is None:
            app.redoc_url = "/redoc"
        if getattr(app, "openapi_url", None) is None:
            app.openapi_url = "/openapi.json"

        # Patch Swagger UI to use correct path for OpenAPI schema
        # Since Traefik strips the path prefix, we need Swagger UI to load openapi.json
        # relative to the current path, not from root
        from starlette.middleware.base import BaseHTTPMiddleware
        from fastapi.responses import HTMLResponse

        class SwaggerUIPatchMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                if request.url.path == "/docs" and response.status_code == 200:
                    body = b""
                    if hasattr(response, 'body_iterator'):
                        async for chunk in response.body_iterator:
                            body += chunk
                    elif hasattr(response, 'body'):
                        body = response.body if isinstance(response.body, bytes) else response.body.encode('utf-8')

                    content_type = response.headers.get('content-type', '')
                    if 'text/html' in content_type or body.startswith(b'<!'):
                        html = body.decode('utf-8')
                        html = html.replace("url: '/openapi.json'", "url: 'openapi.json'")
                        html = html.replace('url: "/openapi.json"', 'url: "openapi.json"')
                        new_headers = dict(response.headers)
                        new_headers.pop('content-length', None)
                        return HTMLResponse(content=html, status_code=response.status_code, headers=new_headers)
                return response

        app.add_middleware(SwaggerUIPatchMiddleware)

    app = add_health_wrapper(app)
    
    print("Starting uvicorn server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
