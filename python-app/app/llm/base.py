from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.llm.types import ChatMessage, LLMResponse, ModelInfo, ProviderInfo


class LLMConnector(ABC):
    """
    Abstract Base Interface for LLM Providers.

    All concrete provider connectors (OpenAI, Anthropic, Gemini, Groq, Ollama, etc.)
    implement this interface to ensure uniform invocation across different LLM backends.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model or self.get_default_model()
        self.custom_params = custom_params or {}

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the unique identifier string for this provider."""
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        """Return human-readable name of the provider."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Return default model ID used when none is specified."""
        pass

    @abstractmethod
    def get_supported_models(self) -> List[ModelInfo]:
        """Return the list of models supported by this provider."""
        pass

    @abstractmethod
    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate chat completion for the given conversation messages.

        Args:
            messages: List of ChatMessage objects with roles and content.
            model: Specific model identifier or None to use default.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum token generation limit.
            **kwargs: Extra provider-specific parameters.
        """
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Test and validate whether the configured credentials (API key / endpoint) are valid.
        Returns True if valid, raises an exception or returns False if invalid.
        """
        pass

    def get_provider_info(self) -> ProviderInfo:
        """Return comprehensive metadata regarding the provider and its models."""
        return ProviderInfo(
            provider=self.get_provider_name(),
            display_name=self.get_display_name(),
            requires_api_key=self.requires_api_key(),
            requires_base_url=self.requires_base_url(),
            default_base_url=self.get_default_base_url(),
            default_model=self.get_default_model(),
            models=self.get_supported_models(),
        )

    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key by default."""
        return True

    def requires_base_url(self) -> bool:
        """Whether this provider requires a custom base URL by default."""
        return False

    def get_default_base_url(self) -> Optional[str]:
        """Return default endpoint URL if applicable."""
        return None

    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """Helper to invoke with a simple single user prompt string."""
        response = await self.generate_chat(
            messages=[ChatMessage(role="user", content=prompt)],
            **kwargs,
        )
        return response.content
