from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """
    Open universal chat request schema.
    Supports optional conversation ID, user ID, request ID, model, provider, etc.
    Both snake_case and camelCase parameters are accepted.
    """
    message: str = Field(..., min_length=1, description="The message prompt to send")
    conversation_id: Optional[int] = Field(None, alias="conversationId", description="Optional existing conversation ID.")
    provider: Optional[str] = Field(None, description="LLM provider (e.g. openai, anthropic, gemini, groq, ollama).")
    model: Optional[str] = Field(None, description="Model identifier. If None, default provider model is used.")
    system_prompt: Optional[str] = Field(None, alias="systemPrompt", description="Optional system instruction for the LLM")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, alias="maxTokens", ge=1, description="Max tokens to generate")
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="extraParams", description="Additional provider parameters")
    user_id: Optional[int] = Field(None, alias="userId", description="Optional user ID for tracking/analytics")
    request_id: Optional[str] = Field(None, alias="requestId", description="Optional custom request ID UUID")

    model_config = ConfigDict(populate_by_name=True)


class ChatResponse(BaseModel):
    """Chat completion response with inference metrics."""
    response: str
    conversation_id: int
    provider: str
    model: str
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    status: str = "SUCCESS"
    latency_ms: Optional[int] = None
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    finish_reason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
