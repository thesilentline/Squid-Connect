from typing import Any, Dict, List, Optional
import httpx

from app.llm.base import LLMConnector
from app.llm.types import ChatMessage, LLMProviderEnum, LLMResponse, ModelInfo


class OpenAIConnector(LLMConnector):
    """Connector for OpenAI API and OpenAI-compatible endpoints."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"

    SUPPORTED_MODELS = [
        ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            provider=LLMProviderEnum.OPENAI.value,
            description="Flagship multimodal model with high intelligence and fast response.",
            context_window=128000,
            max_output_tokens=4096,
        ),
        ModelInfo(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider=LLMProviderEnum.OPENAI.value,
            description="Affordable, fast small model for everyday lightweight tasks.",
            context_window=128000,
            max_output_tokens=16384,
        ),
        ModelInfo(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            provider=LLMProviderEnum.OPENAI.value,
            description="High-capability model for complex reasoning and tasks.",
            context_window=128000,
            max_output_tokens=4096,
        ),
        ModelInfo(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            provider=LLMProviderEnum.OPENAI.value,
            description="Legacy fast and cost-effective model.",
            context_window=16385,
            max_output_tokens=4096,
        ),
    ]

    def get_provider_name(self) -> str:
        return LLMProviderEnum.OPENAI.value

    def get_display_name(self) -> str:
        return "OpenAI"

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
            raise ValueError("OpenAI API key is missing. Please configure your credentials.")

        target_model = model or self.default_model or self.DEFAULT_MODEL
        endpoint_url = f"{self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if "organization" in self.custom_params:
            headers["OpenAI-Organization"] = self.custom_params["organization"]

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

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
                raise RuntimeError(f"OpenAI API error ({response.status_code}): {error_msg}")

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
        """Validate credentials by sending a lightweight models list request."""
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
