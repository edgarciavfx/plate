"""ComfyExportJob — runs the display-referred PNG export for a PlateSession.

Produces a 16-bit PNG sequence (scaled to a max width, display transform
baked in) in a 'comfy/' subfolder of the shot directory, ready to feed to
ComfyUI without a manual Nuke round-trip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..media.ffmpeg import export_png_sequence
from ..models.plate_session import PlateSession

if TYPE_CHECKING:
    from ..color import ColorTransform


class ComfyExportJob:
    """Wraps the FFmpeg PNG export step so it can be scheduled, retried,
    or reported on independently of the rest of the pipeline.
    """

    def __init__(
        self,
        session: PlateSession,
        max_width: int = 1024,
        frame_padding: int = 6,
        color_transform: "ColorTransform | None" = None,
    ):
        self.session = session
        self.max_width = max_width
        self.frame_padding = frame_padding
        self.color_transform = color_transform

    def run(self) -> int:
        session = self.session
        if session.metadata is None:
            raise RuntimeError("PlateSession has no metadata — run probe first.")

        comfy_dir = session.comfy_export_dir
        frame_count = export_png_sequence(
            source_path=session.source_path,
            frame_range=session.frame_range,
            fps=session.metadata.fps,
            png_dir=comfy_dir,
            shot_name=session.frame_base_name,
            max_width=self.max_width,
            frame_padding=self.frame_padding,
            color_transform=self.color_transform,
        )
        session.comfy_dir = comfy_dir
        session.comfy_pattern = f"{session.frame_base_name}.%0{self.frame_padding}d.png"
        session.comfy_frames = frame_count
        session.comfy_max_width = self.max_width
        session.comfy_color_transform = self.color_transform
        return frame_count
