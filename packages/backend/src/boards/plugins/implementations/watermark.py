"""Watermark plugin that adds a visible watermark to image artifacts."""

from __future__ import annotations

from pathlib import Path

from ...generators.artifacts import ArtifactTypeName
from ...logging import get_logger
from ..base import BaseArtifactPlugin, PluginContext, PluginResult

logger = get_logger(__name__)


class WatermarkPlugin(BaseArtifactPlugin):
    """Adds a visible watermark overlay to image artifacts.

    The watermark image is composited onto the generated image at the
    specified position with the given opacity.

    Requires Pillow (PIL) to be installed.
    """

    name = "watermark"
    description = "Adds visible watermark to images"
    supported_artifact_types: list[ArtifactTypeName] = ["image"]

    def __init__(
        self,
        watermark_image_path: str,
        position: str = "bottom-right",
        opacity: float = 0.5,
        margin: int = 10,
    ) -> None:
        self.watermark_image_path = Path(watermark_image_path)
        self.position = position
        self.opacity = max(0.0, min(1.0, opacity))
        self.margin = margin

    async def execute(self, context: PluginContext) -> PluginResult:
        try:
            from PIL import Image

            artifact = Image.open(context.file_path)
            if artifact.mode != "RGBA":
                artifact = artifact.convert("RGBA")

            watermark = Image.open(self.watermark_image_path)
            if watermark.mode != "RGBA":
                watermark = watermark.convert("RGBA")

            # Apply opacity to the watermark
            if self.opacity < 1.0:
                alpha = watermark.getchannel("A")
                alpha = alpha.point(lambda p: int(p * self.opacity))
                watermark.putalpha(alpha)

            # Calculate position
            x, y = self._calculate_position(artifact.size, watermark.size)

            # Composite the watermark onto the artifact
            artifact.paste(watermark, (x, y), watermark)

            # Convert back to original mode if needed (e.g. JPEG doesn't support RGBA)
            file_ext = context.file_path.suffix.lower()
            if file_ext in (".jpg", ".jpeg"):
                artifact = artifact.convert("RGB")

            artifact.save(context.file_path)

            logger.info(
                "watermark_applied",
                generation_id=context.generation_id,
                position=self.position,
                opacity=self.opacity,
            )

            return PluginResult(success=True)

        except ImportError:
            return PluginResult(
                success=False,
                error_message="Pillow (PIL) is required for the watermark plugin",
                fail_generation=False,
            )
        except Exception as e:
            return PluginResult(
                success=False,
                error_message=f"Watermarking failed: {e}",
                fail_generation=False,  # Watermark failure is non-critical
            )

    def _calculate_position(
        self,
        image_size: tuple[int, int],
        watermark_size: tuple[int, int],
    ) -> tuple[int, int]:
        """Calculate the (x, y) position for the watermark."""
        img_w, img_h = image_size
        wm_w, wm_h = watermark_size
        m = self.margin

        positions = {
            "top-left": (m, m),
            "top-right": (img_w - wm_w - m, m),
            "bottom-left": (m, img_h - wm_h - m),
            "bottom-right": (img_w - wm_w - m, img_h - wm_h - m),
            "center": ((img_w - wm_w) // 2, (img_h - wm_h) // 2),
        }

        return positions.get(self.position, positions["bottom-right"])
