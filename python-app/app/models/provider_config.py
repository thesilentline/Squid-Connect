from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ProviderConfig(Base):
    """
    Universal LLM provider configuration and credentials table.
    Stores API keys, base URLs, and default models for each provider.
    """
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    encrypted_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    default_model: Mapped[str] = mapped_column(String(100), nullable=False)

    custom_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
