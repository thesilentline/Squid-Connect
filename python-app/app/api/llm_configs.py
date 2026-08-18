from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.llm.factory import LLMFactory
from app.llm.types import ModelInfo, ProviderInfo
from app.schemas.llm_config import (
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderValidateResponse,
)
from app.services.llm_config_service import LLMConfigService

router = APIRouter()


@router.get("/providers", response_model=List[ProviderInfo], summary="List all supported LLM providers and models")
async def list_supported_providers():
    """Retrieve metadata for all supported LLM providers and their available models."""
    return LLMFactory.get_all_providers_info()


@router.get("/providers/{provider}/models", response_model=List[ModelInfo], summary="List models for a specific provider")
async def list_provider_models(provider: str):
    """Retrieve supported models for a specific LLM provider."""
    try:
        return LLMFactory.get_provider_models(provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/configs", response_model=ProviderConfigResponse, status_code=status.HTTP_201_CREATED, summary="Save or update provider credentials")
async def save_provider_config(
    config_in: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Store or update LLM provider credentials and settings (OpenAI, Anthropic, Gemini, Groq, Ollama).
    """
    service = LLMConfigService(db)
    try:
        return await service.save_provider_credentials(config_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/configs", response_model=List[ProviderConfigResponse], summary="List all configured LLM providers")
async def list_all_provider_configs(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all stored provider configurations with masked API keys."""
    service = LLMConfigService(db)
    return await service.get_all_configs()


@router.get("/configs/{provider}", response_model=ProviderConfigResponse, summary="Get config for a specific provider")
async def get_provider_config(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve configuration for a specific provider."""
    service = LLMConfigService(db)
    cfg = await service.get_provider_config(provider)
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration found for provider '{provider}'.",
        )
    return cfg


@router.post("/configs/{provider}/validate", response_model=ProviderValidateResponse, summary="Validate credentials against provider API")
async def validate_provider_credentials(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Test and verify that the stored API key/endpoint can successfully connect to the provider."""
    service = LLMConfigService(db)
    return await service.validate_provider(provider)


@router.delete("/configs/{provider}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete provider config")
async def delete_provider_config(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a configured provider credentials."""
    service = LLMConfigService(db)
    deleted = await service.delete_config(provider)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for provider '{provider}' not found.",
        )
