"""API routes aggregator module."""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.llm_configs import router as llm_configs_router

api_router = APIRouter()

api_router.include_router(llm_configs_router, prefix="/llm", tags=["LLM Provider Credentials & Models"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])

__all__ = [
    "api_router",
    "health_router",
    "chat_router",
    "conversations_router",
    "llm_configs_router",
]
