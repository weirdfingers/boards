"""Pydantic models for progress updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Literal
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
    message: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    artifacts: List[ArtifactInfo] = []
    timestamp: datetime = datetime.now(timezone.utc)
