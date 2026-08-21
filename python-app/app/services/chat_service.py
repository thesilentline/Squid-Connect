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
        - Persists user prompt and assistant response (or error message on failure) in DB
        - Dispatches structured events conforming to Java Inference and InferencePayload entities
        """
        request_id = request.request_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        start_perf = time.perf_counter()
        user_id = request.user_id

        provider_name = request.provider or "unknown"
        target_model = request.model or "unknown"
        conversation_id = request.conversation_id
        conversation = None
        user_message_record = None
        formatted_history: List[Dict[str, Any]] = []
        history_limit = settings.MAX_HISTORY_MESSAGES

        try:
            if conversation_id:
                conversation = await self.conversation_repo.get_by_id(conversation_id)
                if not conversation:
                    title_preview = request.message[:35].strip() + ("..." if len(request.message) > 35 else "")
                    conversation = await self.conversation_repo.create_conversation(
                        title=title_preview,
                        provider=request.provider,
                        model=request.model,
                    )
                    conversation_id = conversation.id
            else:
                title_preview = request.message[:35].strip() + ("..." if len(request.message) > 35 else "")
                conversation = await self.conversation_repo.create_conversation(
                    title=title_preview,
                    provider=request.provider,
                    model=request.model,
                )
                conversation_id = conversation.id

            user_message_record = await self.message_repo.create_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )

            user_message_id = user_message_record.id
            user_message_created_at = user_message_record.created_at.isoformat() if user_message_record.created_at else None

            history_records = await self.message_repo.get_messages_by_conversation(
                conversation_id=conversation_id,
                limit=history_limit,
            )

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

            connector, resolved_model, provider_config = await self.llm_config_service.resolve_connector(
                provider=request.provider or (conversation.provider if conversation else None),
                model=request.model or (conversation.model if conversation else None),
            )
            provider_name = connector.get_provider_name()
            target_model = resolved_model

            if conversation and (not conversation.provider or not conversation.model):
                try:
                    if not conversation.provider:
                        conversation.provider = provider_name
                    if not conversation.model:
                        conversation.model = target_model
                    await self.session.commit()
                except Exception:
                    pass

            llm_messages: List[ChatMessage] = []
            if request.system_prompt:
                llm_messages.append(ChatMessage(role="system", content=request.system_prompt))

            for msg in history_records:
                llm_messages.append(ChatMessage(role=msg.role, content=msg.content))

            llm_response: LLMResponse = await connector.generate_chat(
                messages=llm_messages,
                model=target_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                **(request.extra_params or {}),
            )
            completed_at = datetime.now(timezone.utc)
            latency_ms = int(round((time.perf_counter() - start_perf) * 1000))

            assistant_message_record = await self.message_repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=llm_response.content,
                tokens_used=llm_response.tokens_total,
            )

            full_turn_history = (formatted_history + [
                {
                    "id": assistant_message_record.id,
                    "role": "assistant",
                    "content": llm_response.content,
                    "tokens_used": llm_response.tokens_total,
                    "created_at": assistant_message_record.created_at.isoformat() if assistant_message_record.created_at else None,
                }
            ])[-history_limit:]

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
                conversation_id=conversation_id,
                input_tokens=llm_response.tokens_prompt,
                output_tokens=llm_response.tokens_completion,
                total_tokens=llm_response.tokens_total,
                user_id=user_id,
                metadata=success_metadata,
            )

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
            error_message_str = str(error)
            error_type_str = error.__class__.__name__
            error_content = error_message_str

            if not conversation_id:
                try:
                    title_preview = request.message[:35].strip() + ("..." if len(request.message) > 35 else "")
                    fallback_conv = await self.conversation_repo.create_conversation(
                        title=title_preview,
                        provider=request.provider or (provider_name if provider_name != "unknown" else None),
                        model=request.model or (target_model if target_model != "unknown" else None),
                    )
                    conversation_id = fallback_conv.id
                except Exception as conv_err:
                    print(f"[ChatService] Could not create fallback conversation on error: {conv_err}")

            user_msg_id = locals().get("user_message_id")
            user_msg_created_at = locals().get("user_message_created_at")

            if conversation_id and not user_msg_id:
                try:
                    user_message_record = await self.message_repo.create_message(
                        conversation_id=conversation_id,
                        role="user",
                        content=request.message,
                    )
                    user_msg_id = user_message_record.id
                    user_msg_created_at = user_message_record.created_at.isoformat() if user_message_record.created_at else None
                except Exception as usr_err:
                    print(f"[ChatService] Could not save user prompt on error: {usr_err}")

            failed_msg_id = None
            failed_msg_created_at = None
            if conversation_id:
                try:
                    failed_message_record = await self.message_repo.create_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_content,
                        tokens_used=None,
                    )
                    failed_msg_id = failed_message_record.id
                    failed_msg_created_at = failed_message_record.created_at.isoformat() if failed_message_record.created_at else None
                except Exception as err_rec_err:
                    print(f"[ChatService] Could not save failed message to conversation: {err_rec_err}")

            failed_history = list(formatted_history)
            if user_msg_id and not any(m.get("id") == user_msg_id for m in failed_history):
                failed_history.append({
                    "id": user_msg_id,
                    "role": "user",
                    "content": request.message,
                    "tokens_used": None,
                    "created_at": user_msg_created_at,
                })
            if failed_msg_id:
                failed_history.append({
                    "id": failed_msg_id,
                    "role": "assistant",
                    "content": error_content,
                    "tokens_used": None,
                    "created_at": failed_msg_created_at,
                })
            failed_history = failed_history[-history_limit:]

            failed_metadata = {
                "conversation_id": conversation_id,
                "system_prompt": request.system_prompt,
                "temperature": request.temperature,
                "extra_params": request.extra_params,
                "conversation_history": failed_history,
                "error": error_message_str,
                "error_type": error_type_str,
            }

            logged_error = error_message_str
            print(f"*****************************[ChatService] error={logged_error}********************************")

            try:
                await event_publisher.publish_inference_failed(
                    request_id=request_id,
                    model=target_model if target_model != "unknown" else (request.model or "unknown"),
                    provider=provider_name if provider_name != "unknown" else (request.provider or "unknown"),
                    input_text=request.message,
                    error_message=error_message_str,
                    started_at=started_at,
                    completed_at=completed_at,
                    latency_ms=latency_ms,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    metadata=failed_metadata,
                    error_type=error_type_str,
                )
            except Exception as pub_err:
                print(f"[ChatService] Could not publish failed inference event: {pub_err}")

            return ChatResponse(
                response=error_content,
                conversation_id=conversation_id,
                provider=provider_name if provider_name != "unknown" else (request.provider or "unknown"),
                model=target_model if target_model != "unknown" else (request.model or "unknown"),
                request_id=request_id,
                user_id=user_id,
                status=InferenceStatus.FAILED.value,
                latency_ms=latency_ms,
                tokens_prompt=None,
                tokens_completion=None,
                tokens_total=None,
                finish_reason="error",
            )

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
