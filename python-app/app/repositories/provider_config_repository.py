from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_config import ProviderConfig


class ProviderConfigRepository:
    """Repository handling universal LLM provider configurations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_provider(self, provider: str) -> Optional[ProviderConfig]:
        """Get config for a specific provider."""
        query = select(ProviderConfig).where(
            ProviderConfig.provider == provider.lower()
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_default_config(self) -> Optional[ProviderConfig]:
        """Get the primary/default active LLM configuration."""
        query = select(ProviderConfig).where(
            ProviderConfig.is_active == True,
            ProviderConfig.is_default == True,
        )
        result = await self.session.execute(query)
        config = result.scalar_one_or_none()
        
        if not config:
            query = select(ProviderConfig).where(
                ProviderConfig.is_active == True
            ).order_by(ProviderConfig.updated_at.desc())
            result = await self.session.execute(query)
            config = result.scalar_one_or_none()

        return config

    async def list_all_configs(self) -> List[ProviderConfig]:
        """List all stored LLM provider configurations."""
        query = select(ProviderConfig).order_by(ProviderConfig.provider)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert_config(
        self,
        provider: str,
        encrypted_api_key: Optional[str],
        base_url: Optional[str],
        default_model: str,
        custom_parameters: Optional[Dict[str, Any]] = None,
        is_default: bool = False,
        is_active: bool = True,
    ) -> ProviderConfig:
        """Create or update provider configuration."""
        provider_name = provider.lower()
        
        if is_default:
            await self.session.execute(
                update(ProviderConfig).values(is_default=False)
            )

        existing = await self.get_by_provider(provider_name)
        if existing:
            if encrypted_api_key is not None:
                existing.encrypted_api_key = encrypted_api_key
            if base_url is not None:
                existing.base_url = base_url
            if default_model:
                existing.default_model = default_model
            if custom_parameters is not None:
                existing.custom_parameters = custom_parameters
            existing.is_default = is_default
            existing.is_active = is_active
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            config = ProviderConfig(
                provider=provider_name,
                encrypted_api_key=encrypted_api_key,
                base_url=base_url,
                default_model=default_model,
                custom_parameters=custom_parameters or {},
                is_default=is_default,
                is_active=is_active,
            )
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)
            return config

    async def delete_config(self, provider: str) -> bool:
        """Delete a provider configuration."""
        config = await self.get_by_provider(provider)
        if config:
            await self.session.delete(config)
            await self.session.commit()
            return True
        return False
