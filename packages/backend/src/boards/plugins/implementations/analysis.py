"""Content analysis plugin skeleton.

Analyzes generated content and attaches metadata without modifying the
file itself. Intended as an extension point for safety checks, quality
scoring, or classification.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ...generators.artifacts import ArtifactTypeName
from ...logging import get_logger
from ..base import BaseArtifactPlugin, PluginContext, PluginResult

logger = get_logger(__name__)


class ContentAnalysisPlugin(BaseArtifactPlugin):
    """Runs content analysis and attaches metadata.

    This is a skeleton implementation. Subclass or replace with your own
    analysis logic (e.g. NSFW detection, quality scoring).
    """

    name = "content-analysis"
    description = "Runs content analysis and attaches metadata"
    supported_artifact_types: list[ArtifactTypeName] = []  # All types

    async def execute(self, context: PluginContext) -> PluginResult:
        logger.info(
            "content_analysis_executed",
            generation_id=context.generation_id,
            artifact_type=context.artifact_type,
            file_size_bytes=context.file_size_bytes,
        )

        return PluginResult(
            success=True,
            metadata={
                "content_analysis": {
                    "status": "skeleton — no analysis performed",
                    "artifact_type": context.artifact_type,
                    "file_size_bytes": context.file_size_bytes,
                },
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
