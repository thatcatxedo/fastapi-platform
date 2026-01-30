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
APP_ROOT_PATH = os.getenv("APP_ROOT_PATH", "")

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

def add_trailing_slash_redirect(app, root_path: str):
    """
    Middleware to redirect requests without trailing slash to include one.
    This ensures relative URLs in HTML forms resolve correctly.
    """
    async def wrapped(scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            print(f"[trailing_slash] path={path}")
            # If request is to root without trailing slash, redirect to add it
            # The browser sees the full URL, so we redirect to root_path + "/"
            if path == "" or path == "/":
                # Check if the original request had a trailing slash by looking at raw_path
                raw_path = scope.get("raw_path", b"/").decode()
                if not raw_path.endswith("/"):
                    redirect_url = f"{root_path}/"
                    await send({
                        "type": "http.response.start",
                        "status": 308,  # Permanent redirect that preserves method
                        "headers": [
                            (b"content-type", b"text/plain"),
                            (b"location", redirect_url.encode()),
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": b"Redirecting...",
                    })
                    return
        await app(scope, receive, send)
    return wrapped

def add_health_wrapper(app):
    async def wrapped(scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            # Debug: log incoming path
            print(f"[health_wrapper] type=http, path={path}, root_path={scope.get('root_path', '')}")
            if path == "/health":
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

    # Add trailing slash redirect if we have a root path configured
    if APP_ROOT_PATH:
        print(f"Configuring app with root_path: {APP_ROOT_PATH}")
        app = add_trailing_slash_redirect(app, APP_ROOT_PATH)

    print("Starting uvicorn server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, root_path=APP_ROOT_PATH)

if __name__ == "__main__":
    main()
