from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProviderConfigCreate(BaseModel):
    """Payload to store or update LLM provider configuration and API key."""
    provider: str = Field(..., description="Provider name, e.g. openai, anthropic, gemini, groq, ollama")
    api_key: Optional[str] = Field(None, description="Provider API key")
    base_url: Optional[str] = Field(None, description="Custom base URL / endpoint (for Ollama, vLLM, local models)")
    default_model: Optional[str] = Field(None, description="Default model (e.g. gpt-4o, claude-3-5-sonnet)")
    custom_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom extra parameters")
    is_default: bool = Field(True, description="Whether to set this provider as the system default")


class ProviderConfigUpdate(BaseModel):
    """Payload for updating an existing provider config."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    custom_parameters: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ProviderConfigResponse(BaseModel):
    """Response containing safe provider configuration details."""
    id: int
    provider: str
    masked_api_key: str
    has_api_key: bool
    base_url: Optional[str] = None
    default_model: str
    custom_parameters: Optional[Dict[str, Any]] = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProviderValidateResponse(BaseModel):
    """Response returned when testing provider credentials."""
    provider: str
    is_valid: bool
    message: str
