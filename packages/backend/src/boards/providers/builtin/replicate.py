from __future__ import annotations

from ..base import BaseProvider, ProviderConfig


class ReplicateProvider(BaseProvider):
    name = "replicate"

    async def validate_credentials(self) -> bool:
        return bool(self.config.api_key)

    def get_base_url(self) -> str:
        return self.config.endpoint or "https://api.replicate.com/v1"

