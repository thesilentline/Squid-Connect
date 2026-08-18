from typing import Any, Dict, List, Optional
import httpx

from app.llm.base import LLMConnector
from app.llm.types import ChatMessage, LLMProviderEnum, LLMResponse, ModelInfo


class GeminiConnector(LLMConnector):
    """Connector for Google Gemini API."""

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-1.5-flash"

    SUPPORTED_MODELS = [
        ModelInfo(
            id="gemini-1.5-flash",
            name="Gemini 1.5 Flash",
            provider=LLMProviderEnum.GEMINI.value,
            description="Fast, high-throughput model with a 1M token context window.",
            context_window=1000000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            provider=LLMProviderEnum.GEMINI.value,
            description="Highly capable model for complex reasoning and large-scale multimodal inputs.",
            context_window=2000000,
            max_output_tokens=8192,
        ),
        ModelInfo(
            id="gemini-2.0-flash-exp",
            name="Gemini 2.0 Flash (Experimental)",
            provider=LLMProviderEnum.GEMINI.value,
            description="Next-generation multimodal model with state-of-the-art speed and quality.",
            context_window=1048576,
            max_output_tokens=8192,
        ),
        ModelInfo(
                    id="gemini-2.5-flash-lite",
                    name="Gemini 2.5 Flash Lite",
                    provider=LLMProviderEnum.GEMINI.value,
                    description="Next-generation multimodal model with state-of-the-art speed and quality.",
                    context_window=1048576,
                    max_output_tokens=8192,
                ),
        ModelInfo(
                            id="gemini-3.5-flash",
                            name="Gemini 3.5 Flash",
                            provider=LLMProviderEnum.GEMINI.value,
                            description="Next-generation multimodal model with state-of-the-art speed and quality.",
                            context_window=1048576,
                            max_output_tokens=8192,
                        ),
    ]

    def get_provider_name(self) -> str:
        return LLMProviderEnum.GEMINI.value

    def get_display_name(self) -> str:
        return "Google Gemini"

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
            raise ValueError("Google Gemini API key is missing. Please configure your credentials.")

        target_model = model or self.default_model or self.DEFAULT_MODEL
        base_api_url = self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL
        endpoint_url = f"{base_api_url}/models/{target_model}:generateContent?key={self.api_key}"

        # Convert chat messages to Gemini content parts
        contents = []
        system_instruction = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content}]
                })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint_url, json=payload)
            
            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                raise RuntimeError(f"Gemini API error ({response.status_code}): {error_msg}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini returned empty candidate list.")

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            text_content = "".join([part.get("text", "") for part in parts])
            
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount")
            completion_tokens = usage.get("candidatesTokenCount")
            total_tokens = usage.get("totalTokenCount")

            return LLMResponse(
                content=text_content,
                provider=self.get_provider_name(),
                model=target_model,
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                tokens_total=total_tokens,
                finish_reason=candidate.get("finishReason"),
                raw_response=data,
            )

    async def validate_credentials(self) -> bool:
        if not self.api_key:
            return False

        base_api_url = self.base_url.rstrip('/') if self.base_url else self.DEFAULT_BASE_URL
        endpoint_url = f"{base_api_url}/models?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint_url)
                return resp.status_code == 200
        except Exception:
            return False
