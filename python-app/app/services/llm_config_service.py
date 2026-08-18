from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key, encrypt_api_key, mask_api_key
from app.llm.base import LLMConnector
from app.llm.factory import LLMFactory
from app.models.provider_config import ProviderConfig
from app.repositories.provider_config_repository import ProviderConfigRepository
from app.schemas.llm_config import (
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderValidateResponse,
)


class LLMConfigService:
    """
    Business service managing universal LLM provider credentials, encryption, and runtime connector resolution.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_repo = ProviderConfigRepository(session)

    async def save_provider_credentials(self, config_in: ProviderConfigCreate) -> ProviderConfigResponse:
        """
        Store or update LLM credentials for a provider.
        """
        provider_name = config_in.provider.lower()
        
        # Determine default model if none supplied
        default_model = config_in.default_model
        if not default_model:
            try:
                temp_connector = LLMFactory.get_connector(provider_name)
                default_model = temp_connector.get_default_model()
            except Exception:
                default_model = "default"

        # Encrypt the API key
        encrypted_key = encrypt_api_key(config_in.api_key) if config_in.api_key else None

        # Upsert into database
        db_config = await self.config_repo.upsert_config(
            provider=provider_name,
            encrypted_api_key=encrypted_key,
            base_url=config_in.base_url,
            default_model=default_model,
            custom_parameters=config_in.custom_parameters or {},
            is_default=config_in.is_default,
            is_active=True,
        )

        return self._build_response(db_config, raw_key=config_in.api_key)

    async def get_all_configs(self) -> List[ProviderConfigResponse]:
        """Fetch all stored LLM provider configurations with masked API keys."""
        configs = await self.config_repo.list_all_configs()
        responses: List[ProviderConfigResponse] = []
        for cfg in configs:
            raw_key = decrypt_api_key(cfg.encrypted_api_key)
            responses.append(self._build_response(cfg, raw_key=raw_key))
        return responses

    async def get_provider_config(self, provider: str) -> Optional[ProviderConfigResponse]:
        """Fetch a specific provider config."""
        cfg = await self.config_repo.get_by_provider(provider)
        if not cfg:
            return None
        raw_key = decrypt_api_key(cfg.encrypted_api_key)
        return self._build_response(cfg, raw_key=raw_key)

    async def resolve_connector(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[LLMConnector, str, Optional[ProviderConfig]]:
        """
        Dynamically retrieve stored credentials from the database for the provider (or default),
        decrypt the API key, and instantiate the proper LLM connector via LLMFactory.
        """
        db_config: Optional[ProviderConfig] = None
        if provider:
            db_config = await self.config_repo.get_by_provider(provider)
        else:
            db_config = await self.config_repo.get_default_config()

        # If a DB config exists, use its credentials
        if db_config:
            provider_name = db_config.provider
            decrypted_api_key = decrypt_api_key(db_config.encrypted_api_key)
            target_model = model or db_config.default_model
            base_url = db_config.base_url
            custom_params = db_config.custom_parameters or {}
        else:
            # Fallback to requested provider or OpenAI
            provider_name = (provider or "openai").lower()
            decrypted_api_key = None
            target_model = model or "default"
            base_url = None
            custom_params = {}

        # Instantiate LLM connector via Factory Pattern
        connector = LLMFactory.get_connector(
            provider=provider_name,
            api_key=decrypted_api_key,
            base_url=base_url,
            default_model=target_model,
            custom_params=custom_params,
        )

        return connector, (target_model if target_model != "default" else connector.get_default_model()), db_config

    async def validate_provider(self, provider: str) -> ProviderValidateResponse:
        """Test provider credentials against live API endpoint."""
        try:
            connector, _, _ = await self.resolve_connector(provider=provider)
            is_valid = await connector.validate_credentials()
            if is_valid:
                return ProviderValidateResponse(
                    provider=provider,
                    is_valid=True,
                    message="Credentials verified successfully against provider API.",
                )
            else:
                return ProviderValidateResponse(
                    provider=provider,
                    is_valid=False,
                    message="Credentials verification failed. Please check your API key or endpoint.",
                )
        except Exception as e:
            return ProviderValidateResponse(
                provider=provider,
                is_valid=False,
                message=f"Validation error: {str(e)}",
            )

    async def delete_config(self, provider: str) -> bool:
        """Remove a provider config."""
        return await self.config_repo.delete_config(provider)

    def _build_response(
        self,
        cfg: ProviderConfig,
        raw_key: Optional[str] = None,
    ) -> ProviderConfigResponse:
        """Construct safe response schema with masked keys."""
        masked = mask_api_key(raw_key) if raw_key else ("********" if cfg.encrypted_api_key else "")
        return ProviderConfigResponse(
            id=cfg.id,
            provider=cfg.provider,
            masked_api_key=masked,
            has_api_key=bool(cfg.encrypted_api_key),
            base_url=cfg.base_url,
            default_model=cfg.default_model,
            custom_parameters=cfg.custom_parameters,
            is_active=cfg.is_active,
            is_default=cfg.is_default,
            created_at=cfg.created_at,
            updated_at=cfg.updated_at,
        )
