from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm.types import ChatMessage, LLMResponse
from app.models.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationSummary,
    MessageResponse,
)
from app.services.event_publisher_service import InferenceStatus, event_publisher
from app.services.llm_config_service import LLMConfigService


class ChatService:
    """
    Open Universal Chat Orchestraction Service.
    
    Handles:
    - Creating new chat sessions (Feature 1)
    - Browsing and reading existing chat sessions with full request/response history (Feature 2)
    - Sending prompts and generating assistant answers using dynamic LLM providers
    - Publishing realtime inference & payload events (matching Inference & InferencePayload JPA entities)
    - Renaming and deleting chat conversations
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.llm_config_service = LLMConfigService(session)

    async def create_new_chat(self, payload: ConversationCreate) -> ConversationResponse:
        """Feature 1: Start a new empty chat session."""
        provider = payload.provider
        model = payload.model
        if not provider:
            default_config = await self.llm_config_service.config_repo.get_default_config()
            if default_config:
                provider = default_config.provider
                model = model or default_config.default_model

        conversation = await self.conversation_repo.create_conversation(
            title=payload.title or "New Chat",
            provider=provider,
            model=model,
        )

        if payload.system_prompt:
            await self.message_repo.create_message(
                conversation_id=conversation.id,
                role="system",
                content=payload.system_prompt,
            )
            conversation = await self.conversation_repo.get_by_id(conversation.id)

        return self._build_conversation_response(conversation)

    async def get_conversation(self, conversation_id: int) -> Optional[ConversationResponse]:
        """Feature 2: Fetch an existing chat with its complete request/response history."""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None
        return self._build_conversation_response(conversation)

    async def list_chats(self, limit: int = 50) -> List[ConversationSummary]:
        """Feature 2: List all past chats with preview metadata for sidebar browsing."""
        summaries_data = await self.conversation_repo.list_summaries(limit=limit)
        return [ConversationSummary(**s) for s in summaries_data]

    async def rename_chat(self, conversation_id: int, title: str) -> Optional[ConversationResponse]:
        """Rename an existing conversation."""
        updated = await self.conversation_repo.update_title(conversation_id, title)
        if not updated:
            return None
        return self._build_conversation_response(updated)

    async def delete_chat(self, conversation_id: int) -> bool:
        """Delete an existing conversation and all messages."""
        return await self.conversation_repo.delete_conversation(conversation_id)

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process chat prompt:
        - Automatically creates a new conversation or loads the existing one
        - Resolves provider credentials from DB
        - Generates unique requestId and tracks accurate startedAt/completedAt/latencyMs
        - Persists user prompt and assistant response in DB
        - Dispatches structured events conforming to Java Inference and InferencePayload entities
        """
        # 1. Generate unique request identifier and start timestamp
        request_id = request.request_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        user_id = request.user_id

        # 2. Dynamically resolve LLM connector from stored DB credentials
        connector, target_model, provider_config = await self.llm_config_service.resolve_connector(
            provider=request.provider,
            model=request.model,
        )
        provider_name = connector.get_provider_name()

        # 3. Create or load Conversation
        conversation_id = request.conversation_id
        if conversation_id:
            conversation = await self.conversation_repo.get_by_id(conversation_id)
            if not conversation:
                title_preview = request.message[:35].strip() + ("..." if len(request.message) > 35 else "")
                conversation = await self.conversation_repo.create_conversation(
                    title=title_preview,
                    provider=provider_name,
                    model=target_model,
                )
                conversation_id = conversation.id
        else:
            # Start new conversation automatically titled from first prompt
            title_preview = request.message[:35].strip() + ("..." if len(request.message) > 35 else "")
            conversation = await self.conversation_repo.create_conversation(
                title=title_preview,
                provider=provider_name,
                model=target_model,
            )
            conversation_id = conversation.id

        # 4. Save user prompt message to database
        user_message_record = await self.message_repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        # 5. Fetch the latest max 5 messages for multi-turn conversation context
        history_limit = settings.MAX_HISTORY_MESSAGES
        history_records = await self.message_repo.get_messages_by_conversation(
            conversation_id=conversation_id,
            limit=history_limit,
        )

        # Build clean JSON multi-turn history list (max 5)
        formatted_history = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tokens_used": m.tokens_used,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in history_records
        ]

        # 6. Publish PROCESSING / RECEIVED Inference Event (matching Java Inference & InferencePayload)
        request_metadata = {
            "conversation_id": conversation_id,
            "system_prompt": request.system_prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "extra_params": request.extra_params,
            "conversation_history": formatted_history,
        }
        # await event_publisher.publish_inference_processing(
        #     request_id=request_id,
        #     model=target_model,
        #     provider=provider_name,
        #     input_text=request.message,
        #     user_id=user_id,
        #     started_at=started_at,
        #     metadata=request_metadata,
        # )

        # 7. Format chat messages for LLM connector (max 5 recent context)
        llm_messages: List[ChatMessage] = []
        if request.system_prompt:
            llm_messages.append(ChatMessage(role="system", content=request.system_prompt))

        for msg in history_records:
            llm_messages.append(ChatMessage(role=msg.role, content=msg.content))

        # 8. Generate response using the resolved LLM provider connector with latency tracking
        start_perf = time.perf_counter()
        try:
            llm_response: LLMResponse = await connector.generate_chat(
                messages=llm_messages,
                model=target_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                **(request.extra_params or {}),
            )
            completed_at = datetime.now(timezone.utc)
            latency_ms = int(round((time.perf_counter() - start_perf) * 1000))

            # 9. Persist assistant reply to database
            assistant_message_record = await self.message_repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=llm_response.content,
                tokens_used=llm_response.tokens_total,
            )

            # Full history including the generated assistant reply (capped to max 5)
            full_turn_history = (formatted_history + [
                {
                    "id": assistant_message_record.id,
                    "role": "assistant",
                    "content": llm_response.content,
                    "tokens_used": llm_response.tokens_total,
                    "created_at": assistant_message_record.created_at.isoformat() if assistant_message_record.created_at else None,
                }
            ])[-history_limit:]

            # 10. Publish SUCCESS Inference Event (matching Java Inference & InferencePayload)
            success_metadata = {
                "conversation_id": conversation_id,
                "system_prompt": request.system_prompt,
                "finish_reason": llm_response.finish_reason,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "extra_params": request.extra_params,
                "conversation_history": full_turn_history,
            }
            await event_publisher.publish_inference_success(
                request_id=request_id,
                model=llm_response.model,
                provider=llm_response.provider,
                input_text=request.message,
                output_text=llm_response.content,
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=latency_ms,
                input_tokens=llm_response.tokens_prompt,
                output_tokens=llm_response.tokens_completion,
                total_tokens=llm_response.tokens_total,
                user_id=user_id,
                metadata=success_metadata,
            )

            # 11. Return structured response
            return ChatResponse(
                response=llm_response.content,
                conversation_id=conversation_id,
                provider=llm_response.provider,
                model=llm_response.model,
                request_id=request_id,
                user_id=user_id,
                status=InferenceStatus.SUCCESS.value,
                latency_ms=latency_ms,
                tokens_prompt=llm_response.tokens_prompt,
                tokens_completion=llm_response.tokens_completion,
                tokens_total=llm_response.tokens_total,
                finish_reason=llm_response.finish_reason,
            )

        except Exception as error:
            completed_at = datetime.now(timezone.utc)
            latency_ms = int(round((time.perf_counter() - start_perf) * 1000))
            
            # Publish FAILED Inference Event (matching Java Inference & InferencePayload)
            failed_metadata = {
                "conversation_id": conversation_id,
                "system_prompt": request.system_prompt,
                "temperature": request.temperature,
                "extra_params": request.extra_params,
                "conversation_history": formatted_history,
            }
            logged_error = str(error)
            print(f"*****************************[ChatService] error={logged_error}********************************")
            await event_publisher.publish_inference_failed(
                request_id=request_id,
                model=target_model,
                provider=provider_name,
                input_text=request.message,
                error_message=str(error),
                started_at=started_at,
                # input_tokens=input_tokens,
                completed_at=completed_at,
                latency_ms=latency_ms,
                user_id=user_id,
                metadata=failed_metadata,
            )
            raise error

    def _build_conversation_response(self, conv: Conversation) -> ConversationResponse:
        """Helper to build ConversationResponse schema."""
        messages_schema = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                tokens_used=m.tokens_used,
                created_at=m.created_at,
            )
            for m in (conv.messages or [])
        ]

        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            provider=conv.provider,
            model=conv.model,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages_schema,
        )
