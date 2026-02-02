"""
Chat service for AI-assisted app building.
Handles conversation flow, n8n webhook calls, and tool execution.
Supports agentic loops where Claude can iterate (create→test→fix→verify).
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import httpx
from bson import ObjectId

from database import conversations_collection, messages_collection, apps_collection
from config import N8N_WEBHOOK_URL
from .tools import TOOLS, execute_tool
from .models import StreamEvent

logger = logging.getLogger(__name__)

# Safety limit for agentic loops
MAX_TOOL_ITERATIONS = 10


class ChatService:
    """Service for handling AI chat conversations."""

    def __init__(self):
        self.n8n_webhook_url = f"{N8N_WEBHOOK_URL}/chat"
        self.http_client = httpx.AsyncClient(timeout=120.0)

    async def create_conversation(self, user: dict, title: Optional[str] = None) -> dict:
        """Create a new conversation."""
        now = datetime.utcnow()
        conversation = {
            "user_id": user["_id"],
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0
        }
        result = await conversations_collection.insert_one(conversation)
        conversation["_id"] = result.inserted_id
        return conversation

    async def get_conversation(self, conversation_id: str, user: dict) -> Optional[dict]:
        """Get a conversation by ID."""
        try:
            conversation = await conversations_collection.find_one({
                "_id": ObjectId(conversation_id),
                "user_id": user["_id"]
            })
            return conversation
        except Exception:
            return None

    async def list_conversations(
        self,
        user: dict,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[dict], int]:
        """List user's conversations with pagination."""
        query = {"user_id": user["_id"]}
        total = await conversations_collection.count_documents(query)

        conversations = []
        cursor = conversations_collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        async for conv in cursor:
            # Get last message preview
            last_msg = await messages_collection.find_one(
                {"conversation_id": conv["_id"]},
                sort=[("created_at", -1)]
            )
            conv["last_message_preview"] = (
                last_msg["content"][:100] if last_msg else None
            )
            conversations.append(conv)

        return conversations, total

    async def delete_conversation(self, conversation_id: str, user: dict) -> bool:
        """Delete a conversation and its messages."""
        try:
            conv_oid = ObjectId(conversation_id)
        except Exception:
            return False

        # Verify ownership
        conversation = await conversations_collection.find_one({
            "_id": conv_oid,
            "user_id": user["_id"]
        })
        if not conversation:
            return False

        # Delete messages
        await messages_collection.delete_many({"conversation_id": conv_oid})
        # Delete conversation
        await conversations_collection.delete_one({"_id": conv_oid})
        return True

    async def get_messages(
        self,
        conversation_id: str,
        user: dict,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """Get messages for a conversation."""
        try:
            conv_oid = ObjectId(conversation_id)
        except Exception:
            return []

        # Verify conversation ownership
        conversation = await conversations_collection.find_one({
            "_id": conv_oid,
            "user_id": user["_id"]
        })
        if not conversation:
            return []

        messages = []
        cursor = messages_collection.find(
            {"conversation_id": conv_oid}
        ).sort("created_at", 1).skip(skip).limit(limit)
        async for msg in cursor:
            messages.append(msg)
        return messages

    def _build_system_prompt(self, user: dict, app_context: Optional[Dict[str, Any]] = None) -> str:
        """Build system prompt with user context and optional app context."""
        databases = user.get("databases", [])
        db_list = ", ".join([db.get("name", db["id"]) for db in databases]) if databases else "none"

        prompt = f"""You are a friendly, knowledgeable AI assistant helping users build FastAPI and FastHTML applications.

CONVERSATION STYLE:
- Be conversational and helpful, not just a tool-executor
- When users ask questions, ANSWER them directly - don't immediately jump to using tools
- Discuss ideas, explain concepts, and offer opinions when asked
- Ask clarifying questions when requirements are unclear
- Suggest approaches and get user buy-in BEFORE taking action
- It's OK to have a back-and-forth discussion before building anything

Examples of conversational responses:
- "What's the best way to structure my API?" → Discuss REST patterns, give recommendations
- "Should I use FastAPI or FastHTML?" → Explain trade-offs, ask about their use case
- "How does authentication work here?" → Explain the platform's capabilities
- "I'm thinking about building a todo app" → Ask questions, discuss features, THEN offer to build

WHEN TO USE TOOLS vs. JUST TALK:
- Use tools when user explicitly asks you to CREATE, BUILD, DEPLOY, UPDATE, DELETE, or FIX something
- Just talk when user asks HOW, WHY, WHAT, or wants your OPINION
- If unsure, ask: "Would you like me to build that, or should we discuss it more first?"

User Context:
- User ID: {str(user["_id"])}
- Username: {user.get("username", "unknown")}
- Available databases: {db_list}"""

        # Add app context if provided
        if app_context:
            prompt += f"""

Current App Context (user is working on this app):
- App ID: {app_context['app_id']}
- Name: {app_context['name']}
- Status: {app_context.get('status', 'unknown')}
- URL: {app_context.get('url', 'not deployed')}
- Mode: {app_context.get('mode', 'single')}
- Framework: {app_context.get('framework') or 'N/A'}"""

            if app_context.get('code'):
                # Truncate long code to avoid token limits
                code = app_context['code']
                if len(code) > 3000:
                    code = code[:3000] + "\n... (truncated)"
                prompt += f"""

Current code:
```python
{code}
```"""
            elif app_context.get('files'):
                # Show all file contents for multi-file apps
                prompt += "\n\nCurrent files:"
                total_chars = 0
                for filename, content in app_context['files'].items():
                    # Truncate if getting too long
                    if total_chars > 6000:
                        prompt += f"\n\n--- {filename} ---\n(truncated - file not shown)"
                        continue
                    file_content = content
                    if len(file_content) > 2000:
                        file_content = file_content[:2000] + "\n... (truncated)"
                    prompt += f"\n\n--- {filename} ---\n```python\n{file_content}\n```"
                    total_chars += len(file_content)

            prompt += """

IMPORTANT: When the user refers to "the app", "this app", or "my app", they mean the app above.
Use update_app with the app_id above when modifying this app. Do NOT create a new app unless explicitly asked."""

        prompt += """

CRITICAL PLATFORM CONSTRAINTS - YOU MUST FOLLOW THESE:

1. NEVER import uvicorn - The platform starts your app automatically. Do NOT add if __name__ == "__main__" blocks or uvicorn.run().

2. MUST define an 'app' variable:
   - FastAPI: app = FastAPI()
   - FastHTML: app, rt = fast_app() (tuple unpacking for app and route decorator)

3. Allowed imports (ONLY these work):
   fastapi, pydantic, typing, datetime, json, math, random, string, collections, itertools, functools, operator, re, uuid, hashlib, base64, urllib, urllib.parse, fasthtml, fastlite, starlette, os, sys, pathlib, time, enum, dataclasses, decimal, html, http, copy, textwrap, calendar, locale, secrets, statistics, pymongo, bson, jinja2, httpx, slack_sdk, google.auth, googleapiclient

4. FORBIDDEN operations (will cause validation failure):
   - eval(), exec(), compile(), __import__()
   - open(), file() - no file system access
   - subprocess, os.system, os.popen
   - input(), raw_input()

5. File modes:
   - Single-file: Just write the code, uploaded as main.py
   - Multi-file: Use files dict with entrypoint=app.py
     - Max 10 files, max 100KB per file, 500KB total
     - ALL files must be .py files
     - Can import between your own files (e.g., from models import Todo)

6. Database access:
   - MongoDB URI: os.getenv("PLATFORM_MONGO_URI")
   - Always check if URI exists before connecting
   - Example: uri = os.getenv("PLATFORM_MONGO_URI"); if uri: client = MongoClient(uri)

Platform Info:
- Each app gets URL: https://app-{app_id}.gatorlunch.com
- Apps auto-restart on deploy, health checks at /health
- Framework detection: Use 'fastapi' or 'fasthtml' in framework parameter

Available Tools:
- list_templates: See available starter templates
- get_template_code: Fetch template code to use as reference
- validate_code_only: Check code passes validation BEFORE deploying
- create_app / update_app: Deploy apps
- test_endpoint: Verify deployed endpoints work (GET /todos, POST /items, etc.)
- diagnose_app: Analyze failing apps (pod status, errors, suggested fixes)
- get_app_logs: Read recent logs for debugging

AGENTIC WORKFLOW - You can chain multiple tools:
- When creating apps: validate_code_only → create_app → test_endpoint → (fix if needed)
- When debugging: diagnose_app → get_app_logs → update_app → test_endpoint
- When using templates: list_templates → get_template_code → adapt code → validate_code_only → create_app

Best Practices:
- DISCUSS before you BUILD - understand what the user really wants
- Ask clarifying questions: "Do you want this to have authentication?" "Should it store data?"
- When user asks for "app like X template", discuss what they want to customize first
- Use validate_code_only before create_app to catch errors early
- After deploying, use test_endpoint to verify the app works
- If app fails, use diagnose_app then get_app_logs to find the issue
- Keep code simple and focused on user requirements
- For database apps, always use PLATFORM_MONGO_URI env var

PLATFORM KNOWLEDGE BASE - Common Issues & Solutions:

ERROR: CrashLoopBackOff / App won't start:
- Missing 'app' variable: Code MUST define `app = FastAPI()` or `app, rt = fast_app()`
- Importing uvicorn: NEVER import uvicorn - the platform runs your app automatically
- Syntax error: Check for typos, missing colons, unmatched brackets
- Import error: Module not in allowed list - suggest alternatives

ERROR: 502 Bad Gateway:
- App crashed during startup - use get_app_logs to see the Python traceback
- Usually a runtime error in module-level code (code that runs at import time)
- Check for exceptions in global scope or class definitions

ERROR: "No module named X":
- Import not in the allowed list
- Common alternatives: requests→httpx, flask→fastapi, sqlite3→use MongoDB instead

ERROR: Database connection fails:
- Missing env var check: Always do `uri = os.getenv("PLATFORM_MONGO_URI"); if uri: client = MongoClient(uri)`
- Never assume the env var exists - check first, then connect

ERROR: App works locally but not on platform:
- File system access (open/write files) - NOT allowed, use database instead
- Hardcoded localhost URLs - use relative paths or environment variables
- Threading/multiprocessing - limited support, prefer async patterns

DEBUGGING WORKFLOW (follow this order):
1. App failing? → Use diagnose_app first (pod status, K8s events, quick diagnosis)
2. Need details? → Use get_app_logs to see the actual Python traceback
3. Found the issue? → Use update_app to fix, then test_endpoint to verify

TEMPLATE RECOMMENDATIONS:
- "Simple API" → FastAPI Basic - REST endpoints, JSON, OpenAPI docs
- "Web UI / HTML pages" → FastHTML Basic or FastHTML HTMX
- "Store data / database" → MongoDB Todo template (requires database_id)
- "Interactive page with state" → FastHTML Counter (client-side) or HTMX (server)
- "Real-time updates" → FastHTML HTMX with polling or SSE

FASTAPI vs FASTHTML - When to use which:
- FastAPI: REST APIs, JSON responses, OpenAPI/Swagger docs, Pydantic validation, API-first apps
- FastHTML: HTML pages, htmx interactivity, server-side rendering, simpler for UIs, rapid prototyping
- Pick one framework per app for clarity

HANDLING VAGUE USER REQUESTS:
- "Build me an app" → Ask: What should it do? API or UI? Need to store data?
- "Make it better" → Ask: What's not working? Performance? Missing features? UI issues?
- "Fix this" / "Why isn't it working?" → Use diagnose_app + get_app_logs FIRST, then explain what you found
- "Like the X template" → Fetch the template with get_template_code, discuss customizations before building

Remember: You're a helpful collaborator, not just a code generator. Have a conversation!"""

        return prompt

    def _format_messages_for_llm(self, messages: List[dict]) -> List[dict]:
        """Format conversation messages for LLM API."""
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            # Include tool results if present
            if msg.get("tool_calls"):
                formatted_msg["tool_calls"] = msg["tool_calls"]
            formatted.append(formatted_msg)
        return formatted

    async def _call_claude_via_n8n(
        self,
        messages: List[dict],
        system_prompt: str,
        user_id: str
    ) -> tuple[List[dict], str, Optional[str]]:
        """
        Make a single call to Claude via n8n.

        Returns:
            (events, stop_reason, error)
            - events: list of parsed events (text, tool_call, etc.)
            - stop_reason: "end_turn", "tool_use", etc.
            - error: error message if any
        """
        request_data = {
            "messages": messages,
            "system_prompt": system_prompt,
            "tools": TOOLS,
            "user_id": user_id
        }

        events = []
        stop_reason = "end_turn"

        try:
            async with self.http_client.stream(
                "POST",
                self.n8n_webhook_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"n8n webhook error: {response.status_code} - {error_text}")
                    return [], "error", f"LLM service error: {response.status_code}"

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        events.append({"type": "text", "content": line})
                        continue

                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if not isinstance(item, dict):
                            events.append({"type": "text", "content": str(item)})
                            continue

                        event_type = item.get("type", "text")

                        if event_type == "done":
                            stop_reason = item.get("stop_reason", "end_turn")
                        else:
                            events.append(item)

        except httpx.TimeoutException:
            return [], "error", "Request timed out"
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            return [], "error", f"Connection error: {str(e)}"

        return events, stop_reason, None

    async def process_message_stream(
        self,
        user: dict,
        conversation_id: str,
        content: str,
        app_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and stream the response.
        Supports agentic loops where Claude can use multiple tools in sequence.
        Yields Server-Sent Events (SSE) formatted strings.
        """
        try:
            conv_oid = ObjectId(conversation_id)
        except Exception:
            yield self._sse_event(StreamEvent(type="error", error="Invalid conversation ID"))
            return

        # Verify conversation exists and belongs to user
        conversation = await conversations_collection.find_one({
            "_id": conv_oid,
            "user_id": user["_id"]
        })
        if not conversation:
            yield self._sse_event(StreamEvent(type="error", error="Conversation not found"))
            return

        # Fetch app context if app_id provided
        app_context = None
        if app_id:
            app = await apps_collection.find_one({
                "app_id": app_id,
                "user_id": user["_id"]
            })
            if app:
                app_context = {
                    "app_id": app["app_id"],
                    "name": app["name"],
                    "status": app.get("status"),
                    "url": app.get("deployment_url"),
                    "mode": app.get("mode", "single"),
                    "framework": app.get("framework"),
                    "code": app.get("code") if app.get("mode") != "multi" else None,
                    # Include actual file contents for multi-file apps so AI can modify them
                    "files": app.get("files") if app.get("mode") == "multi" else None
                }
                logger.info(f"Chat using app context: {app_context['app_id']} ({app_context['name']})")

        # Save user message
        now = datetime.utcnow()
        user_message = {
            "conversation_id": conv_oid,
            "role": "user",
            "content": content,
            "created_at": now
        }
        await messages_collection.insert_one(user_message)

        # Load conversation history
        history = await self.get_messages(conversation_id, user)
        messages = self._format_messages_for_llm(history)
        system_prompt = self._build_system_prompt(user, app_context)
        user_id = str(user["_id"])

        # Agentic loop - continue calling Claude until done or max iterations
        all_assistant_content = ""
        all_tool_calls = []
        iteration = 0

        while iteration < MAX_TOOL_ITERATIONS:
            iteration += 1
            logger.info(f"Claude call iteration {iteration}")

            # Call Claude
            events, stop_reason, error = await self._call_claude_via_n8n(
                messages, system_prompt, user_id
            )

            if error:
                yield self._sse_event(StreamEvent(type="error", error=error))
                return

            # Process events from this iteration
            iteration_text = ""
            iteration_tool_calls = []

            for event in events:
                event_type = event.get("type", "text")

                if event_type == "text":
                    text = event.get("content", "")
                    iteration_text += text
                    all_assistant_content += text
                    yield self._sse_event(StreamEvent(type="text", content=text))

                elif event_type == "tool_call":
                    tool_name = event.get("name")
                    tool_input = event.get("input", {})
                    tool_id = event.get("id", f"tool_{len(all_tool_calls)}")

                    yield self._sse_event(StreamEvent(
                        type="tool_start",
                        tool=tool_name,
                        tool_input=tool_input
                    ))

                    # Execute the tool
                    tool_result = await execute_tool(tool_name, tool_input, user)

                    iteration_tool_calls.append({
                        "id": tool_id,
                        "name": tool_name,
                        "input": tool_input,
                        "result": tool_result
                    })
                    all_tool_calls.append({
                        "id": tool_id,
                        "name": tool_name,
                        "input": tool_input,
                        "result": tool_result
                    })

                    yield self._sse_event(StreamEvent(
                        type="tool_result",
                        tool=tool_name,
                        result=tool_result
                    ))

                elif event_type == "error":
                    yield self._sse_event(StreamEvent(
                        type="error",
                        error=event.get("error", "Unknown error")
                    ))
                    return

            # Check if we should continue the loop
            if stop_reason != "tool_use" or not iteration_tool_calls:
                # Claude is done - no more tool calls
                logger.info(f"Agentic loop complete after {iteration} iteration(s), stop_reason={stop_reason}")
                break

            # Claude wants to continue after tool use - build continuation messages
            logger.info(f"Continuing agentic loop with {len(iteration_tool_calls)} tool results")

            # Build assistant message with tool_use blocks
            assistant_content_blocks = []
            if iteration_text:
                assistant_content_blocks.append({
                    "type": "text",
                    "text": iteration_text
                })
            for tc in iteration_tool_calls:
                assistant_content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"]
                })

            # Build user message with tool_result blocks
            tool_result_blocks = []
            for tc in iteration_tool_calls:
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(tc["result"])
                })

            # Add to messages for next iteration
            messages.append({
                "role": "assistant",
                "content": assistant_content_blocks
            })
            messages.append({
                "role": "user",
                "content": tool_result_blocks
            })

        if iteration >= MAX_TOOL_ITERATIONS:
            logger.warning(f"Agentic loop hit max iterations ({MAX_TOOL_ITERATIONS})")
            yield self._sse_event(StreamEvent(
                type="text",
                content=f"\n\n[Reached maximum tool iterations ({MAX_TOOL_ITERATIONS}). Stopping here.]"
            ))

        # Save assistant message with all tool calls
        assistant_message = {
            "conversation_id": conv_oid,
            "role": "assistant",
            "content": all_assistant_content,
            "tool_calls": all_tool_calls if all_tool_calls else None,
            "created_at": datetime.utcnow()
        }
        await messages_collection.insert_one(assistant_message)

        # Update conversation
        await conversations_collection.update_one(
            {"_id": conv_oid},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {"message_count": 2}  # user + assistant
            }
        )

        # Generate title if this is the first message
        if conversation.get("title") is None and conversation.get("message_count", 0) == 0:
            title = content[:50] + "..." if len(content) > 50 else content
            await conversations_collection.update_one(
                {"_id": conv_oid},
                {"$set": {"title": title}}
            )

        yield self._sse_event(StreamEvent(type="done"))

    def _sse_event(self, event: StreamEvent) -> str:
        """Format a StreamEvent as an SSE message."""
        data = event.model_dump(exclude_none=True)
        return f"data: {json.dumps(data)}\n\n"


# Singleton instance
chat_service = ChatService()
