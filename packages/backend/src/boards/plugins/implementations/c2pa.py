"""C2PA signing plugin stub.

Embeds C2PA (Coalition for Content Provenance and Authenticity) provenance
metadata into image and video artifacts. Requires the ``c2pa-python``
package and valid signing credentials.

This is a stub implementation — the signing logic is not yet implemented.
"""

from __future__ import annotations

from pathlib import Path

from ...generators.artifacts import ArtifactTypeName
from ...logging import get_logger
from ..base import BaseArtifactPlugin, PluginContext, PluginResult

logger = get_logger(__name__)


class C2PASigningPlugin(BaseArtifactPlugin):
    """Signs artifacts with C2PA Content Credentials.

    This is a stub implementation. When the ``c2pa-python`` package is
    available, this plugin will embed a C2PA manifest into supported
    artifact types, recording provenance information such as the
    generator name and prompt.
    """

    name = "c2pa-signing"
    description = "Signs artifacts with C2PA Content Credentials"
    supported_artifact_types: list[ArtifactTypeName] = ["image", "video"]

    def __init__(
        self,
        signing_key_path: str = "",
        certificate_path: str = "",
        claim_generator: str = "Boards/1.0",
    ) -> None:
        self.signing_key_path = Path(signing_key_path) if signing_key_path else None
        self.certificate_path = Path(certificate_path) if certificate_path else None
        self.claim_generator = claim_generator

    async def execute(self, context: PluginContext) -> PluginResult:
        logger.warning(
            "c2pa_signing_not_implemented",
            generation_id=context.generation_id,
        )
        return PluginResult(
            success=True,
            metadata={"c2pa_status": "stub — signing not yet implemented"},
        )
