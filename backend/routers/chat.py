"""
Chat routes for AI-assisted app building.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator

from auth import get_current_user
from chat.service import chat_service
from chat.rate_limiter import chat_rate_limiter
from chat.active_streams import active_streams
from chat.models import (
    ConversationCreate,
    MessageCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new chat conversation."""
    conversation = await chat_service.create_conversation(user, data.title)
    return ConversationResponse(
        id=str(conversation["_id"]),
        title=conversation.get("title"),
        created_at=conversation["created_at"].isoformat(),
        updated_at=conversation["updated_at"].isoformat(),
        message_count=0
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """List user's chat conversations."""
    conversations, total = await chat_service.list_conversations(user, skip, limit)
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=str(conv["_id"]),
                title=conv.get("title"),
                created_at=conv["created_at"].isoformat(),
                updated_at=conv["updated_at"].isoformat(),
                message_count=conv.get("message_count", 0),
                last_message_preview=conv.get("last_message_preview")
            )
            for conv in conversations
        ],
        total=total
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a conversation with its messages."""
    conversation = await chat_service.get_conversation(conversation_id, user)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await chat_service.get_messages(conversation_id, user)
    return ConversationDetailResponse(
        id=str(conversation["_id"]),
        title=conversation.get("title"),
        created_at=conversation["created_at"].isoformat(),
        updated_at=conversation["updated_at"].isoformat(),
        message_count=conversation.get("message_count", 0),
        messages=[
            MessageResponse(
                id=str(msg["_id"]),
                role=msg["role"],
                content=msg["content"],
                tool_calls=msg.get("tool_calls"),
                created_at=msg["created_at"].isoformat()
            )
            for msg in messages
        ]
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a conversation and its messages."""
    success = await chat_service.delete_conversation(conversation_id, user)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "message": "Conversation deleted"}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    user: dict = Depends(get_current_user)
):
    """
    Send a message and stream the AI response.
    Returns Server-Sent Events (SSE) stream.

    Rate limits:
    - Per-minute and per-hour message limits
    - Only one active stream per user at a time
    """
    user_id = str(user["_id"])

    # Check rate limit
    allowed, error_msg = await chat_rate_limiter.check_rate_limit(user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    # Check concurrent streams
    if not await active_streams.acquire(user_id):
        raise HTTPException(
            status_code=429,
            detail="Only one active chat stream allowed. Please wait for the current response to complete."
        )

    # Verify conversation exists
    conversation = await chat_service.get_conversation(conversation_id, user)
    if not conversation:
        await active_streams.release(user_id)
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Record message for rate limiting
    await chat_rate_limiter.record_message(user_id)

    # Wrap the stream generator to ensure we release the slot when done
    async def stream_with_cleanup() -> AsyncGenerator[str, None]:
        try:
            async for chunk in chat_service.process_message_stream(
                user, conversation_id, data.content, data.app_id
            ):
                yield chunk
        finally:
            await active_streams.release(user_id)
            logger.debug(f"Released stream slot for user {user_id}")

    return StreamingResponse(
        stream_with_cleanup(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
