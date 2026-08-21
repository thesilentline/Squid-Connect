from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key, encrypt_api_key, mask_api_key
from app.llm.base import LLMConnector
from app.llm.factory import LLMFactory
from app.llm.types import ModelInfo, ProviderInfo
from app.models.provider_config import ProviderConfig
from app.repositories.provider_config_repository import ProviderConfigRepository
from app.schemas.llm_config import (
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderValidateResponse,
)


class LLMConfigService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_repo = ProviderConfigRepository(session)

    async def save_provider_credentials(self, config_in: ProviderConfigCreate) -> ProviderConfigResponse:
        provider_name = config_in.provider.lower()

        custom_params = dict(config_in.custom_parameters or {})
        if config_in.models is not None:
            cleaned_models = [m.strip() for m in config_in.models if isinstance(m, str) and m.strip()]
            custom_params["models"] = cleaned_models
        else:
            cleaned_models = custom_params.get("models", [])

        default_model = config_in.default_model
        if not default_model:
            if cleaned_models and len(cleaned_models) > 0:
                default_model = cleaned_models[0]
            else:
                try:
                    temp_connector = LLMFactory.get_connector(provider_name)
                    default_model = temp_connector.get_default_model()
                except Exception:
                    default_model = "default"

        encrypted_key = encrypt_api_key(config_in.api_key) if config_in.api_key else None

        db_config = await self.config_repo.upsert_config(
            provider=provider_name,
            encrypted_api_key=encrypted_key,
            base_url=config_in.base_url,
            default_model=default_model,
            custom_parameters=custom_params,
            is_default=config_in.is_default,
            is_active=True,
        )

        return self._build_response(db_config, raw_key=config_in.api_key)

    async def get_all_configs(self) -> List[ProviderConfigResponse]:
        configs = await self.config_repo.list_all_configs()
        responses: List[ProviderConfigResponse] = []
        for cfg in configs:
            raw_key = decrypt_api_key(cfg.encrypted_api_key)
            responses.append(self._build_response(cfg, raw_key=raw_key))
        return responses

    async def get_provider_config(self, provider: str) -> Optional[ProviderConfigResponse]:
        cfg = await self.config_repo.get_by_provider(provider.lower())
        if not cfg:
            return None
        raw_key = decrypt_api_key(cfg.encrypted_api_key)
        return self._build_response(cfg, raw_key=raw_key)

    async def get_provider_models(self, provider: str) -> List[ModelInfo]:
        provider_name = provider.lower()
        cfg = await self.config_repo.get_by_provider(provider_name)
        if cfg and cfg.custom_parameters and cfg.custom_parameters.get("models"):
            models_list = cfg.custom_parameters["models"]
            if isinstance(models_list, list) and len(models_list) > 0:
                return [
                    ModelInfo(id=m, name=m, provider=provider_name, description="User configured model")
                    for m in models_list
                ]
        try:
            return LLMFactory.get_provider_models(provider_name)
        except Exception:
            if cfg and cfg.default_model:
                return [ModelInfo(id=cfg.default_model, name=cfg.default_model, provider=provider_name)]
            return [ModelInfo(id="default", name="default", provider=provider_name)]

    async def get_all_providers_info(self) -> List[ProviderInfo]:
        configs = await self.config_repo.list_all_configs()
        config_map = {c.provider.lower(): c for c in configs}
        base_infos = LLMFactory.get_all_providers_info()
        result: List[ProviderInfo] = []
        seen_providers = set()

        for info in base_infos:
            p_key = info.name.lower()
            seen_providers.add(p_key)
            if p_key in config_map:
                cfg = config_map[p_key]
                if cfg.custom_parameters and cfg.custom_parameters.get("models"):
                    custom_models = cfg.custom_parameters["models"]
                    if isinstance(custom_models, list) and len(custom_models) > 0:
                        info.models = [
                            ModelInfo(id=m, name=m, provider=p_key, description="Configured model")
                            for m in custom_models
                        ]
                        info.default_model = cfg.default_model or custom_models[0]
            result.append(info)

        for p_key, cfg in config_map.items():
            if p_key not in seen_providers:
                custom_models = cfg.custom_parameters.get("models", [cfg.default_model]) if cfg.custom_parameters else [cfg.default_model]
                result.append(
                    ProviderInfo(
                        name=p_key,
                        display_name=p_key.capitalize(),
                        description="Custom configured provider",
                        default_model=cfg.default_model,
                        models=[
                            ModelInfo(id=m, name=m, provider=p_key, description="Configured model")
                            for m in custom_models
                        ],
                    )
                )
        return result

    async def resolve_connector(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[LLMConnector, str, Optional[ProviderConfig]]:
        db_config: Optional[ProviderConfig] = None
        if provider:
            db_config = await self.config_repo.get_by_provider(provider.lower())
        else:
            db_config = await self.config_repo.get_default_config()

        if db_config:
            provider_name = db_config.provider
            decrypted_api_key = decrypt_api_key(db_config.encrypted_api_key)
            target_model = model or db_config.default_model
            base_url = db_config.base_url
            custom_params = db_config.custom_parameters or {}
        else:
            provider_name = (provider or "openai").lower()
            decrypted_api_key = None
            target_model = model or "default"
            base_url = None
            custom_params = {}

        connector = LLMFactory.get_connector(
            provider=provider_name,
            api_key=decrypted_api_key,
            base_url=base_url,
            default_model=target_model,
            custom_params=custom_params,
        )

        return connector, (target_model if target_model != "default" else connector.get_default_model()), db_config

    async def validate_provider(self, provider: str) -> ProviderValidateResponse:
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
        return await self.config_repo.delete_config(provider.lower())

    def _build_response(
        self,
        cfg: ProviderConfig,
        raw_key: Optional[str] = None,
    ) -> ProviderConfigResponse:
        masked = mask_api_key(raw_key) if raw_key else ("********" if cfg.encrypted_api_key else "")

        models_list: List[str] = []
        if cfg.custom_parameters and isinstance(cfg.custom_parameters.get("models"), list):
            models_list = [m for m in cfg.custom_parameters["models"] if isinstance(m, str) and m.strip()]

        if not models_list:
            try:
                models_list = [m.id for m in LLMFactory.get_provider_models(cfg.provider)]
            except Exception:
                models_list = [cfg.default_model] if cfg.default_model else ["default"]

        return ProviderConfigResponse(
            id=cfg.id,
            provider=cfg.provider,
            masked_api_key=masked,
            has_api_key=bool(cfg.encrypted_api_key),
            base_url=cfg.base_url,
            default_model=cfg.default_model,
            models=models_list,
            custom_parameters=cfg.custom_parameters,
            is_active=cfg.is_active,
            is_default=cfg.is_default,
            created_at=cfg.created_at,
            updated_at=cfg.updated_at,
        )
