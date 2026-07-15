"""ProxyJob — runs the H.264 proxy export for a PlateSession."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..color import ColorTransform
from ..media.ffmpeg import export_proxy
from ..models.plate_session import PlateSession


class ProxyJob:
    """Wraps the FFmpeg proxy export step."""

    def __init__(
        self,
        session: PlateSession,
        max_width: int = 1920,
        crf: int = 18,
        color_transform: Optional[ColorTransform] = None,
        burn_in: Optional[list[str]] = None,
    ):
        self.session = session
        self.max_width = max_width
        self.crf = crf
        self.color_transform = color_transform
        self.burn_in = burn_in

    def run(self) -> Path:
        session = self.session
        if session.metadata is None:
            raise RuntimeError("PlateSession has no metadata — run probe first.")

        proxy_path = session.output_dir / session.proxy_filename
        export_proxy(
            source_path=session.source_path,
            frame_range=session.frame_range,
            fps=session.metadata.fps,
            proxy_path=proxy_path,
            max_width=self.max_width,
            crf=self.crf,
            color_transform=self.color_transform,
            burn_in=self.burn_in,
        )
        session.proxy_path = proxy_path
        return proxy_path
