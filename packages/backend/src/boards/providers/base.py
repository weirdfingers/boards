"""Base classes and config models for Providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    additional_headers: Optional[Dict[str, str]] = None
    additional_config: Dict[str, Any] = {}


class BaseProvider(ABC):
    name: str

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate provider credentials."""

    def build_headers(self) -> Dict[str, str]:
        """Default auth headers; override as needed."""
        headers: Dict[str, str] = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.additional_headers:
            headers.update(self.config.additional_headers)
        return headers

    def get_base_url(self) -> str:
        return self.config.endpoint or ""

