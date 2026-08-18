from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMProviderEnum(str, Enum):
    """Supported LLM Provider identifiers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """Chat message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Unified chat message representation across all providers."""
    role: str = MessageRole.USER.value
    content: str
    name: Optional[str] = None


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: str
    provider: str
    model: str
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class ModelInfo(BaseModel):
    """Metadata describing a specific model supported by a provider."""
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: bool = True


class ProviderInfo(BaseModel):
    """Metadata describing a provider, its required credentials, and supported models."""
    provider: str
    display_name: str
    requires_api_key: bool = True
    requires_base_url: bool = False
    default_base_url: Optional[str] = None
    default_model: str
    models: List[ModelInfo] = Field(default_factory=list)
