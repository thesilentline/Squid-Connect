from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Schema representing a single message in a conversation."""
    id: int
    conversation_id: int
    role: str
    content: str
    tokens_used: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationCreate(BaseModel):
    """Payload to start a new chat session."""
    title: Optional[str] = Field("New Chat", description="Optional title for the chat")
    provider: Optional[str] = Field(None, description="Preferred LLM provider (e.g. openai, anthropic, gemini, groq, ollama)")
    model: Optional[str] = Field(None, description="Preferred model identifier")
    system_prompt: Optional[str] = Field(None, alias="systemPrompt", description="Optional initial system prompt")

    model_config = ConfigDict(populate_by_name=True)


class ConversationUpdate(BaseModel):
    """Payload to update conversation metadata (e.g. rename chat)."""
    title: str = Field(..., min_length=1, max_length=255, description="New title for the chat")


class ConversationSummary(BaseModel):
    """Summary item for browsing list of previous chats."""
    id: int
    title: str
    provider: Optional[str] = None
    model: Optional[str] = None
    message_count: int = 0
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationResponse(BaseModel):
    """Full conversation with request & response history."""
    id: int
    title: str
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SendPromptInConversationRequest(BaseModel):
    """Payload to send a prompt within an existing conversation."""
    message: str = Field(..., min_length=1, description="Prompt message to send to the assistant")
    provider: Optional[str] = Field(None, description="Override LLM provider for this turn")
    model: Optional[str] = Field(None, description="Override model for this turn")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, alias="maxTokens", ge=1)
    user_id: Optional[int] = Field(None, alias="userId", description="Optional user ID")
    request_id: Optional[str] = Field(None, alias="requestId", description="Optional request ID")
    system_prompt: Optional[str] = Field(None, alias="systemPrompt", description="Optional system prompt")
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="extraParams", description="Extra provider parameters")

    model_config = ConfigDict(populate_by_name=True)
