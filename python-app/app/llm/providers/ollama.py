from typing import Any, Dict, List, Optional
import httpx

from app.llm.base import LLMConnector
from app.llm.types import ChatMessage, LLMProviderEnum, LLMResponse, ModelInfo


class OllamaConnector(LLMConnector):
    """Connector for local or remote Ollama and generic OpenAI-compatible local servers."""

    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "llama3.2"

    SUPPORTED_MODELS = [
        ModelInfo(
            id="llama3.2",
            name="Llama 3.2 (Local)",
            provider=LLMProviderEnum.OLLAMA.value,
            description="Locally run Meta Llama 3.2 model.",
            context_window=128000,
            max_output_tokens=4096,
        ),
        ModelInfo(
            id="mistral",
            name="Mistral 7B (Local)",
            provider=LLMProviderEnum.OLLAMA.value,
            description="Fast and capable local open-weights model.",
            context_window=32768,
            max_output_tokens=4096,
        ),
        ModelInfo(
            id="deepseek-r1",
            name="DeepSeek R1 (Local)",
            provider=LLMProviderEnum.OLLAMA.value,
            description="Reasoning-focused local model.",
            context_window=64000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="qwen2.5",
            name="Qwen 2.5 (Local)",
            provider=LLMProviderEnum.OLLAMA.value,
            description="Multilingual high-performance local model.",
            context_window=128000,
            max_output_tokens=8192,
        ),
    ]

    def get_provider_name(self) -> str:
        return LLMProviderEnum.OLLAMA.value

    def get_display_name(self) -> str:
        return "Ollama / Local LLM"

    def get_default_model(self) -> str:
        return self.DEFAULT_MODEL

    def get_default_base_url(self) -> Optional[str]:
        return self.DEFAULT_BASE_URL

    def requires_api_key(self) -> bool:
        return False  # Local instances usually don't require an API key

    def requires_base_url(self) -> bool:
        return True

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
        target_model = model or self.default_model or self.DEFAULT_MODEL
        base_api = self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL
        
        # Ensure path ends with chat/completions
        if not base_api.endswith("/v1"):
            endpoint_url = f"{base_api}/api/chat"
            # Standard Ollama native format
            payload = {
                "model": target_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
                "options": {"temperature": temperature},
            }
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
        else:
            endpoint_url = f"{base_api}/chat/completions"
            payload = {
                "model": target_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(endpoint_url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama/Local LLM error ({response.status_code}): {response.text}")

            data = response.json()
            
            # Handle both OpenAI-compatible format and native Ollama format
            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens_prompt = usage.get("prompt_tokens")
                tokens_completion = usage.get("completion_tokens")
                tokens_total = usage.get("total_tokens")
                finish_reason = data["choices"][0].get("finish_reason")
            else:
                content = data.get("message", {}).get("content", "")
                tokens_prompt = data.get("prompt_eval_count")
                tokens_completion = data.get("eval_count")
                tokens_total = (tokens_prompt or 0) + (tokens_completion or 0)
                finish_reason = "stop" if data.get("done") else None

            return LLMResponse(
                content=content,
                provider=self.get_provider_name(),
                model=target_model,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                finish_reason=finish_reason,
                raw_response=data,
            )

    async def validate_credentials(self) -> bool:
        """Validate if the Ollama endpoint is reachable."""
        base_api = self.base_url.rstrip('/') if self.base_url else "http://localhost:11434"
        test_url = f"{base_api}/api/tags" if not base_api.endswith("/v1") else f"{base_api}/models"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(test_url)
                return resp.status_code == 200
        except Exception:
            return False
