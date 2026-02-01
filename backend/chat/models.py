"""
Pydantic models for chat feature
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ConversationCreate(BaseModel):
    """Request model for creating a conversation"""
    title: Optional[str] = None


class MessageCreate(BaseModel):
    """Request model for sending a message"""
    content: str


class ToolCall(BaseModel):
    """A tool call made by the assistant"""
    id: str
    name: str
    input: Dict[str, Any]
    result: Optional[Any] = None


class Message(BaseModel):
    """A message in a conversation"""
    id: str
    role: str  # "user" | "assistant"
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    created_at: datetime


class MessageResponse(BaseModel):
    """Response model for a message"""
    id: str
    role: str
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    created_at: str


class ConversationResponse(BaseModel):
    """Response model for a conversation"""
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message_preview: Optional[str] = None


class ConversationDetailResponse(ConversationResponse):
    """Response model for a conversation with messages"""
    messages: List[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """Response model for listing conversations"""
    conversations: List[ConversationResponse]
    total: int


class StreamEvent(BaseModel):
    """An event in the SSE stream"""
    type: str  # "text" | "tool_start" | "tool_result" | "done" | "error"
    content: Optional[str] = None
    tool: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
