"""Pydantic models for progress updates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel


class ArtifactInfo(BaseModel):
    url: str
    type: str
    metadata: dict = {}


class ProgressUpdate(BaseModel):
    job_id: str
    status: str  # Use string to avoid tight coupling to GraphQL enums
    progress: float
    phase: Literal["queued", "initializing", "processing", "finalizing"]
    message: str | None = None
    estimated_completion: datetime | None = None
    artifacts: list[ArtifactInfo] = []
    timestamp: datetime = datetime.now(UTC)
