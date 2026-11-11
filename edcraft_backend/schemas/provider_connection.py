"""Contracts for user-owned model provider connections."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

ProviderKind = Literal["soclaas", "openai"]


class ProviderConnectionCreate(BaseModel):
    """Create one encrypted, user-owned provider connection."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    kind: ProviderKind
    base_url: str | None = Field(default=None, max_length=500)
    api_key: SecretStr
    default_model: str = Field(min_length=1, max_length=120)
    models: list[str] = Field(default_factory=list, max_length=500)


class ProviderConnectionUpdate(BaseModel):
    """Update display metadata or rotate the stored API key."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: SecretStr | None = None
    default_model: str | None = Field(default=None, min_length=1, max_length=120)
    models: list[str] | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class ProviderProbeRequest(BaseModel):
    """Test credentials before they are stored."""

    model_config = ConfigDict(extra="forbid", strict=True)

    kind: ProviderKind
    base_url: str | None = Field(default=None, max_length=500)
    api_key: SecretStr


class ProviderModelList(BaseModel):
    """Models discovered from a provider's OpenAI-compatible endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: list[str]
    default_model: str | None = None


class ProviderConnectionResponse(BaseModel):
    """Safe connection metadata; the API key is never returned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    name: str
    kind: ProviderKind
    base_url: str | None
    default_model: str
    models: list[str]
    enabled: bool
    key_last4: str
    has_api_key: bool = True
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
