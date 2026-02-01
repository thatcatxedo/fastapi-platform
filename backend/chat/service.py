"""
Chat service for AI-assisted app building.
Handles conversation flow, n8n webhook calls, and tool execution.
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import httpx
from bson import ObjectId

from database import conversations_collection, messages_collection
from config import N8N_WEBHOOK_URL
from .tools import TOOLS, execute_tool
from .models import StreamEvent

logger = logging.getLogger(__name__)


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

    def _build_system_prompt(self, user: dict) -> str:
        """Build system prompt with user context."""
        databases = user.get("databases", [])
        db_list = ", ".join([db.get("name", db["id"]) for db in databases]) if databases else "none"

        return f"""You are an AI assistant helping users build FastAPI and FastHTML applications on a deployment platform.

User Context:
- User ID: {str(user["_id"])}
- Username: {user.get("username", "unknown")}
- Available databases: {db_list}

Platform Capabilities:
- Deploy FastAPI or FastHTML apps instantly
- Single-file or multi-file projects supported
- Each app gets a unique URL (https://app-{{app_id}}.gatorlunch.com)
- Apps can connect to user's MongoDB databases via PLATFORM_MONGO_URI environment variable
- Allowed imports include: fastapi, fasthtml, pydantic, pymongo, jinja2, and common Python stdlib modules

Guidelines:
- Help users create, update, and debug their applications
- Use tools to create and deploy apps when the user requests it
- When creating apps, always validate the code works before deploying
- For database apps, remind users to use os.getenv("PLATFORM_MONGO_URI") for MongoDB connection
- Provide clear explanations of what you're doing
- If an app fails to deploy, use get_app_logs to diagnose the issue
- Keep code simple and focused on the user's requirements"""

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

    async def process_message_stream(
        self,
        user: dict,
        conversation_id: str,
        content: str
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and stream the response.
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
        formatted_history = self._format_messages_for_llm(history)

        # Build request for n8n webhook
        request_data = {
            "messages": formatted_history,
            "system_prompt": self._build_system_prompt(user),
            "tools": TOOLS,
            "user_id": str(user["_id"])
        }

        # Call n8n webhook
        assistant_content = ""
        tool_calls = []

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
                    yield self._sse_event(StreamEvent(
                        type="error",
                        error=f"LLM service error: {response.status_code}"
                    ))
                    return

                # Process streamed response from n8n
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse n8n response format
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        # Might be plain text content
                        assistant_content += line
                        yield self._sse_event(StreamEvent(type="text", content=line))
                        continue

                    # Handle different event types from n8n
                    event_type = data.get("type", "text")

                    if event_type == "text":
                        text = data.get("content", "")
                        assistant_content += text
                        yield self._sse_event(StreamEvent(type="text", content=text))

                    elif event_type == "tool_call":
                        # n8n is requesting a tool call
                        tool_name = data.get("name")
                        tool_input = data.get("input", {})
                        tool_id = data.get("id", f"tool_{len(tool_calls)}")

                        yield self._sse_event(StreamEvent(
                            type="tool_start",
                            tool=tool_name,
                            tool_input=tool_input
                        ))

                        # Execute the tool
                        tool_result = await execute_tool(tool_name, tool_input, user)

                        tool_calls.append({
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

                    elif event_type == "done":
                        # Response complete
                        break

                    elif event_type == "error":
                        yield self._sse_event(StreamEvent(
                            type="error",
                            error=data.get("error", "Unknown error")
                        ))
                        return

        except httpx.TimeoutException:
            yield self._sse_event(StreamEvent(type="error", error="Request timed out"))
            return
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            yield self._sse_event(StreamEvent(type="error", error=f"Connection error: {str(e)}"))
            return

        # Save assistant message with any tool calls
        assistant_message = {
            "conversation_id": conv_oid,
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": tool_calls if tool_calls else None,
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
            # Could call n8n to generate a title, but for now use first few words
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
