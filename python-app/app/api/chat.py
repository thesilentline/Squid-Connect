from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("", response_model=ChatResponse, summary="Send chat prompt and get answer")
async def send_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Open universal chat endpoint:
    - Send a prompt to an LLM provider (OpenAI, Anthropic, Gemini, Groq, Ollama)
    - If conversation_id is omitted, starts a new chat automatically
    - Persists the prompt and response in PostgreSQL
    - Returns the assistant's reply
    """
    service = ChatService(db)
    try:
        return await service.process_chat(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
