from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationSummary,
    ConversationUpdate,
    SendPromptInConversationRequest,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, summary="1. Start a new chat")
async def create_new_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 1: Start a new chat session.
    Creates a new conversation record (with optional title, provider, model, and initial system prompt).
    """
    service = ChatService(db)
    try:
        return await service.create_new_chat(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[ConversationSummary], summary="2. List all past chats")
async def list_all_conversations(
    limit: int = Query(50, ge=1, le=200, description="Max number of past chats to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 2: Browse all past chats.
    Returns a list of older conversations with message counts, timestamps, and last message previews.
    """
    service = ChatService(db)
    return await service.list_chats(limit=limit)


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="2. Go to an older chat with full request/response history")
async def get_conversation_history(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Feature 2: Open an older chat.
    Retrieves the complete conversation session with its entire chronological request & response history (prompts and answers).
    """
    service = ChatService(db)
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found.",
        )
    return conversation


@router.post("/{conversation_id}/messages", response_model=ChatResponse, summary="Give prompt and receive answer in this chat")
async def send_prompt_to_conversation(
    conversation_id: int,
    payload: SendPromptInConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Give a prompt inside an existing conversation and receive the assistant's answer.
    Maintains conversation context history and saves both the prompt and answer in the database.
    """
    chat_request = ChatRequest(
        message=payload.message,
        conversation_id=conversation_id,
        provider=payload.provider,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        user_id=payload.user_id,
        request_id=payload.request_id,
        system_prompt=payload.system_prompt,
        extra_params=payload.extra_params,
    )
    service = ChatService(db)
    try:
        return await service.process_chat(chat_request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{conversation_id}", response_model=ConversationResponse, summary="Rename chat title")
async def rename_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update / rename an existing conversation's title."""
    service = ChatService(db)
    updated = await service.rename_chat(conversation_id, payload.title)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found.",
        )
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a chat")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its message history."""
    service = ChatService(db)
    deleted = await service.delete_chat(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found.",
        )
