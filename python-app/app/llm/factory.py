from typing import Any, Dict, List, Optional, Type
from app.llm.base import LLMConnector
from app.llm.types import LLMProviderEnum, ModelInfo, ProviderInfo
from app.llm.providers.openai import OpenAIConnector
from app.llm.providers.anthropic import AnthropicConnector
from app.llm.providers.gemini import GeminiConnector
from app.llm.providers.groq import GroqConnector
from app.llm.providers.ollama import OllamaConnector


class LLMFactory:
    """
    Factory Pattern & Dynamic Registry for LLM Connectors.

    Allows instantiating provider connectors dynamically at runtime based on:
    - Provider type ('openai', 'anthropic', 'gemini', 'groq', 'ollama', etc.)
    - Stored user API keys & custom base URLs
    - Model selection
    """

    _registry: Dict[str, Type[LLMConnector]] = {
        LLMProviderEnum.OPENAI.value: OpenAIConnector,
        LLMProviderEnum.ANTHROPIC.value: AnthropicConnector,
        LLMProviderEnum.GEMINI.value: GeminiConnector,
        LLMProviderEnum.GROQ.value: GroqConnector,
        LLMProviderEnum.OLLAMA.value: OllamaConnector,
        LLMProviderEnum.CUSTOM.value: OpenAIConnector,
        LLMProviderEnum.AZURE_OPENAI.value: OpenAIConnector,
    }

    @classmethod
    def register_provider(cls, provider_name: str, connector_class: Type[LLMConnector]) -> None:
        """Register a new custom LLM provider connector class."""
        cls._registry[provider_name.lower()] = connector_class

    @classmethod
    def get_connector(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> LLMConnector:
        """
        Instantiate and return the appropriate LLM connector for the given provider.
        """
        provider_key = provider.lower()
        connector_cls = cls._registry.get(provider_key)

        if not connector_cls:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(f"Unsupported LLM provider '{provider}'. Supported providers: {supported}")

        return connector_cls(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            custom_params=custom_params,
        )

    @classmethod
    def get_all_providers_info(cls) -> List[ProviderInfo]:
        """Return information and supported models for all registered providers."""
        infos: List[ProviderInfo] = []
        for provider_key, connector_cls in cls._registry.items():
            if provider_key in [LLMProviderEnum.CUSTOM.value, LLMProviderEnum.AZURE_OPENAI.value]:
                continue
            instance = connector_cls()
            infos.append(instance.get_provider_info())
        return infos

    @classmethod
    def get_provider_models(cls, provider: str) -> List[ModelInfo]:
        """Return supported models for a specific provider."""
        connector_cls = cls._registry.get(provider.lower())
        if not connector_cls:
            raise ValueError(f"Unknown provider '{provider}'")
        instance = connector_cls()
        return instance.get_supported_models()

    @classmethod
    def list_supported_providers(cls) -> List[str]:
        """Return list of supported provider names."""
        return list(cls._registry.keys())
