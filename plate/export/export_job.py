"""ExportJob — runs the EXR sequence export for a PlateSession."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..media.ffmpeg import export_exr_sequence
from ..models.plate_session import PlateSession

if TYPE_CHECKING:
    from ..color import ColorTransform


class ExportJob:
    """Wraps the FFmpeg EXR export step so it can be scheduled, retried,
    or reported on independently of the rest of the pipeline.
    """

    def __init__(
        self,
        session: PlateSession,
        pixel_format: str = "gbrpf32le",
        compression: str = "zip1",
        frame_padding: int = 6,
        color_transform: "ColorTransform | None" = None,
    ):
        self.session = session
        self.pixel_format = pixel_format
        self.compression = compression
        self.frame_padding = frame_padding
        self.color_transform = color_transform

    def run(self) -> int:
        session = self.session
        if session.metadata is None:
            raise RuntimeError("PlateSession has no metadata — run probe first.")
        if session.exr_dir is None:
            raise RuntimeError("PlateSession output dirs not initialized.")

        frame_count = export_exr_sequence(
            source_path=session.source_path,
            frame_range=session.frame_range,
            fps=session.metadata.fps,
            exr_dir=session.exr_dir,
            shot_name=session.shot_name,
            pixel_format=self.pixel_format,
            compression=self.compression,
            frame_padding=self.frame_padding,
            color_transform=self.color_transform,
        )
        session.exported_frames = frame_count
        return frame_count
