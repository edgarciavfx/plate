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
        skip_exr: bool = False,
        skip_proxy: bool = False,
    ):
        self.source = Path(source)
        self.in_frame = in_frame
        self.out_frame = out_frame
        self.output_root = Path(output_root)
        self.start_frame = start_frame
        self.proxy_max_width = proxy_max_width
        self.exr_pixel_format = exr_pixel_format
        self.skip_exr = skip_exr
        self.skip_proxy = skip_proxy

    def run(self, progress=print) -> PipelineResult:
        """Run the full pipeline. `progress` is called with short status
        strings so a CLI or GUI can surface progress without this class
        knowing anything about presentation.
        """
        progress(f"Inspecting {self.source.name}...")
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
        session.ensure_output_dirs()

        if self.skip_proxy:
            progress("Skipping proxy generation.")
        else:
            progress("Generating proxy...")
            ProxyJob(session, max_width=self.proxy_max_width).run()

        if self.skip_exr:
            progress("Skipping EXR generation.")
        else:
            progress(f"Generating EXR sequence ({frame_range.frame_count} frames)...")
            ExportJob(session, pixel_format=self.exr_pixel_format).run()

        progress("Writing manifest...")
        manifest_path = ManifestWriter(session).write()

        progress(f"Done. Shot written to {shot_output_dir}")
        return PipelineResult(session=session, manifest_path=manifest_path)
