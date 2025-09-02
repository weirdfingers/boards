"""Base generator types and REST executor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class GenerationInput(BaseModel):
    pass


class GenerationOutput(BaseModel):
    storage_urls: List[str] = []
    metadata: Dict[str, Any] = {}


class BaseGenerator(ABC):
    name: str
    artifact_type: str

    @abstractmethod
    async def run(self, inputs: Dict[str, Any]) -> GenerationOutput:
        ...

