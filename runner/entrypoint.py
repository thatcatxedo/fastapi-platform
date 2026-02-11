#!/usr/bin/env python3
"""
Entrypoint for FastAPI runner container
Reads user code from ConfigMap and executes it safely
Supports both single-file and multi-file apps
"""
import os
import sys
import time
import threading
import queue
import logging
import importlib.util
from pathlib import Path

logger = logging.getLogger("runner")

CODE_PATH = os.getenv("CODE_PATH", "/code/main.py")
CODE_DIR = os.path.dirname(CODE_PATH)
APP_ID = os.getenv("APP_ID", "unknown")
PLATFORM_MONGO_URI = os.getenv("PLATFORM_MONGO_URI", "")

# Add code directory to Python path for multi-file imports
# This enables: from models import Item, from services import get_items, etc.
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

# Paths to skip for request logging
_SKIP_LOG_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


# =============================================================================
# Request Log Writer (background thread, batched MongoDB writes)
# =============================================================================

class RequestLogWriter:
    """Background thread that batch-writes request logs to MongoDB.

    Completely fault-tolerant: never raises, never blocks the caller.
    Uses a Queue with maxsize to apply backpressure (drops if full).
    """

    def __init__(self, mongo_uri, app_id, batch_size=50, flush_interval=5.0):
        self.mongo_uri = mongo_uri
        self.app_id = app_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue = queue.Queue(maxsize=1000)
        self._collection = None

    def start(self):
        if not self.mongo_uri:
            logger.warning("No PLATFORM_MONGO_URI set, request logging disabled")
            return
        t = threading.Thread(target=self._run, daemon=True, name="request-log-writer")
        t.start()

    def log(self, doc):
        """Enqueue a log document. Drops silently if queue is full."""
        try:
            self._queue.put_nowait(doc)
        except queue.Full:
            pass

    def _get_collection(self):
        if self._collection is None:
            try:
                from pymongo import MongoClient, ASCENDING, DESCENDING
                client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                db = client.get_default_database()
                self._collection = db["_platform_request_logs"]
                # Create indexes (idempotent)
                self._collection.create_index(
                    "timestamp", expireAfterSeconds=604800, background=True
                )
                self._collection.create_index(
                    [("app_id", ASCENDING), ("timestamp", DESCENDING)], background=True
                )
                logger.info("Request log collection initialized with indexes")
            except Exception as e:
                logger.warning(f"Failed to init request log collection: {e}")
                self._collection = None
        return self._collection

    def _run(self):
        while True:
            batch = []
            try:
                item = self._queue.get(timeout=self.flush_interval)
                batch.append(item)
            except queue.Empty:
                continue

            # Drain remaining items up to batch_size
            while len(batch) < self.batch_size:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break

            try:
                collection = self._get_collection()
                if collection is not None and batch:
                    collection.insert_many(batch, ordered=False)
            except Exception as e:
                logger.warning(f"Failed to write request logs: {e}")
                self._collection = None  # Reset to retry connection


# Global writer instance (initialized in main())
_log_writer = None


# =============================================================================
# Request Logging ASGI Middleware
# =============================================================================

def add_request_logging_middleware(app):
    """ASGI middleware that logs request method, path, status, and duration.

    Pure ASGI (not BaseHTTPMiddleware) to avoid response body buffering.
    Writes are non-blocking via the background RequestLogWriter.
    """
    async def middleware(scope, receive, send):
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in _SKIP_LOG_PATHS:
            await app(scope, receive, send)
            return

        start = time.monotonic()
        status_code = 500  # Default if response never starts

        async def send_wrapper(message):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            if _log_writer is not None:
                from datetime import datetime, timezone
                doc = {
                    "app_id": APP_ID,
                    "timestamp": datetime.now(timezone.utc),
                    "method": scope.get("method", ""),
                    "path": path,
                    "query_string": scope.get("query_string", b"").decode(
                        "utf-8", errors="replace"
                    ),
                    "status_code": status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000, 2),
                }
                _log_writer.log(doc)

    return middleware


# =============================================================================
# User Code Loading
# =============================================================================

def load_user_code():
    """Load and validate user code"""
    if not os.path.exists(CODE_PATH):
        print(f"Error: Code file not found at {CODE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CODE_PATH, 'r') as f:
        code = f.read()

    # Basic validation
    if 'app = FastAPI(' not in code and 'fast_app(' not in code and 'FastHTML(' not in code:
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
        import traceback
        print(f"Error executing user code: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    # Get the app instance
    if 'app' not in user_globals:
        print("Error: Code must define an app instance", file=sys.stderr)
        sys.exit(1)

    return user_globals['app']


# =============================================================================
# Health & Swagger Middleware
# =============================================================================

def add_health_wrapper(app):
    """Add /health endpoint for Kubernetes probes"""
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


# =============================================================================
# Main
# =============================================================================

def main():
    global _log_writer

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

    # Middleware wrapping order (outermost first):
    # health wrapper -> request logging -> SwaggerUI patch -> user app
    # This means /health is intercepted before reaching request logging.
    app = add_request_logging_middleware(app)
    app = add_health_wrapper(app)

    # Start request log writer background thread
    if PLATFORM_MONGO_URI:
        _log_writer = RequestLogWriter(PLATFORM_MONGO_URI, APP_ID)
        _log_writer.start()
        print("Request logging enabled")

    print("Starting uvicorn server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
