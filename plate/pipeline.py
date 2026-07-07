"""PlatePipeline — the explicit, end-to-end orchestration:

    Open Footage -> Inspect -> Generate Proxy -> Generate EXRs
    -> Generate Manifest -> Done

Plate owns none of the media logic (that's ffprobe/ffmpeg's job) —
it owns the workflow that stitches those tools together into one
artist-facing action.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .color import ColorTransform
from .export.export_job import ExportJob
from .export.manifest_writer import ManifestWriter
from .export.proxy_job import ProxyJob
from .media.ffprobe import probe
from .models.frame_range import FrameRange
from .models.plate_session import PlateSession


@dataclass
class PipelineResult:
    session: PlateSession
    manifest_path: Path


class PlatePipeline:
    """High-level entry point: give it a source file and an IN/OUT
    selection, get back a fully populated shot folder.
    """

    def __init__(
        self,
        source: str | Path,
        in_frame: int,
        out_frame: int,
        output_root: str | Path = "./output",
        start_frame: Optional[int] = None,
        proxy_max_width: int = 1920,
        exr_pixel_format: str = "gbrpf32le",
        exr_compression: str = "zip1",
        frame_padding: int = 6,
        skip_exr: bool = False,
        skip_proxy: bool = False,
        color_transform: Optional[ColorTransform] = None,
        burn_in: Optional[list[str]] = None,
    ):
        self.source = Path(source)
        self.in_frame = in_frame
        self.out_frame = out_frame
        self.output_root = Path(output_root)
        self.start_frame = start_frame
        self.proxy_max_width = proxy_max_width
        self.exr_pixel_format = exr_pixel_format
        self.exr_compression = exr_compression
        self.frame_padding = frame_padding
        self.skip_exr = skip_exr
        self.skip_proxy = skip_proxy
        self.color_transform = color_transform
        self.burn_in = burn_in

    def run(self, progress=print) -> PipelineResult:
        """Run the full pipeline. `progress` is called with short status
        strings so a CLI or GUI can surface progress without this class
        knowing anything about presentation.

        The callable can accept ``(message, percent)`` where ``percent``
        is an optional integer 0-100.
        """
        progress(f"Inspecting {self.source.name}...", 5)
        metadata = probe(self.source)

        start_frame = self.start_frame if self.start_frame is not None else 0
        frame_range = FrameRange(
            start_frame=start_frame,
            in_frame=self.in_frame,
            out_frame=self.out_frame,
        )

        shot_output_dir = self.output_root / self.source.stem
        session = PlateSession(
            source_path=self.source,
            output_dir=shot_output_dir,
            frame_range=frame_range,
        )
        session.metadata = metadata
        session.color_transform = self.color_transform
        session.ensure_output_dirs()

        if self.skip_proxy:
            progress("Skipping proxy generation.", 30)
        else:
            progress("Generating proxy...", 30)
            ProxyJob(
                session,
                max_width=self.proxy_max_width,
                color_transform=self.color_transform,
                burn_in=self.burn_in,
            ).run()
            progress("Proxy done.", 50)

        if self.skip_exr:
            progress("Skipping EXR generation.", 55)
        else:
            progress(f"Generating EXR sequence ({frame_range.frame_count} frames)...", 55)
            ExportJob(
                session,
                pixel_format=self.exr_pixel_format,
                compression=self.exr_compression,
                frame_padding=self.frame_padding,
                color_transform=self.color_transform,
            ).run()
            progress("EXR sequence done.", 80)

        progress("Writing manifest...", 90)
        manifest_path = ManifestWriter(session).write()

        progress(f"Done. Shot written to {shot_output_dir}", 100)
        return PipelineResult(session=session, manifest_path=manifest_path)
