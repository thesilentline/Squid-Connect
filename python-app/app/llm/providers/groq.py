from typing import Any, Dict, List, Optional
import httpx

from app.llm.base import LLMConnector
from app.llm.types import ChatMessage, LLMProviderEnum, LLMResponse, ModelInfo


class GroqConnector(LLMConnector):
    """Connector for Groq high-speed inference API."""

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    SUPPORTED_MODELS = [
        ModelInfo(
            id="llama-3.3-70b-versatile",
            name="Llama 3.3 70B Versatile",
            provider=LLMProviderEnum.GROQ.value,
            description="State-of-the-art open-weights model running at ultra-fast speeds.",
            context_window=128000,
            max_output_tokens=32768,
        ),
        ModelInfo(
            id="llama-3.1-8b-instant",
            name="Llama 3.1 8B Instant",
            provider=LLMProviderEnum.GROQ.value,
            description="Extreme speed, low-latency model for real-time applications.",
            context_window=128000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="mixtral-8x7b-32768",
            name="Mixtral 8x7B",
            provider=LLMProviderEnum.GROQ.value,
            description="High-quality Mixture of Experts model.",
            context_window=32768,
            max_output_tokens=32768,
        ),
    ]

    def get_provider_name(self) -> str:
        return LLMProviderEnum.GROQ.value

    def get_display_name(self) -> str:
        return "Groq"

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
            raise ValueError("Groq API key is missing. Please configure your credentials.")

        target_model = model or self.default_model or self.DEFAULT_MODEL
        endpoint_url = f"{self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(endpoint_url, json=payload, headers=headers)

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                raise RuntimeError(f"Groq API error ({response.status_code}): {error_msg}")

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                provider=self.get_provider_name(),
                model=target_model,
                tokens_prompt=usage.get("prompt_tokens"),
                tokens_completion=usage.get("completion_tokens"),
                tokens_total=usage.get("total_tokens"),
                finish_reason=choice.get("finish_reason"),
                raw_response=data,
            )

    async def validate_credentials(self) -> bool:
        if not self.api_key:
            return False

        endpoint_url = f"{self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint_url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False
