from typing import Any, Dict, List, Optional
import httpx

from app.llm.base import LLMConnector
from app.llm.types import ChatMessage, LLMProviderEnum, LLMResponse, ModelInfo


class AnthropicConnector(LLMConnector):
    """Connector for Anthropic Claude API."""

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    API_VERSION = "2023-06-01"

    SUPPORTED_MODELS = [
        ModelInfo(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            provider=LLMProviderEnum.ANTHROPIC.value,
            description="State-of-the-art intelligent model for complex reasoning and coding.",
            context_window=200000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            provider=LLMProviderEnum.ANTHROPIC.value,
            description="Ultra-fast, lightweight model with high efficiency.",
            context_window=200000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            provider=LLMProviderEnum.ANTHROPIC.value,
            description="Powerful model for deep research and comprehensive analysis.",
            context_window=200000,
            max_output_tokens=4096,
        ),
    ]

    def get_provider_name(self) -> str:
        return LLMProviderEnum.ANTHROPIC.value

    def get_display_name(self) -> str:
        return "Anthropic"

    def get_default_model(self) -> str:
        return self.DEFAULT_MODEL

    def get_default_base_url(self) -> Optional[str]:
        return self.DEFAULT_BASE_URL

    def get_supported_models(self) -> List[ModelInfo]:
        return self.SUPPORTED_MODELS

    async def generate_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Please configure your credentials.")

        target_model = model or self.default_model or self.DEFAULT_MODEL
        endpoint_url = f"{self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

        system_content: Optional[str] = None
        formatted_messages: List[Dict[str, str]] = []

        for m in messages:
            if m.role == "system":
                system_content = m.content
            else:
                formatted_messages.append({"role": m.role, "content": m.content})

        if not formatted_messages:
            formatted_messages = [{"role": "user", "content": "Hello"}]

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_content:
            payload["system"] = system_content

        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint_url, json=payload, headers=headers)

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                raise RuntimeError(f"Anthropic API error ({response.status_code}): {error_msg}")

            data = response.json()
            content_blocks = data.get("content", [])
            text_content = "".join([block.get("text", "") for block in content_blocks if block.get("type") == "text"])
            usage = data.get("usage", {})

            prompt_tokens = usage.get("input_tokens")
            completion_tokens = usage.get("output_tokens")
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

            return LLMResponse(
                content=text_content,
                provider=self.get_provider_name(),
                model=target_model,
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                tokens_total=total_tokens,
                finish_reason=data.get("stop_reason"),
                raw_response=data,
            )

    async def validate_credentials(self) -> bool:
        """Validate credentials with a minimal 1-token message request."""
        if not self.api_key:
            return False

        endpoint_url = f"{self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint_url, json=payload, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False
