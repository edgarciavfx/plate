"""SessionController — the only object that touches both Qt widgets and
Plate's core (PlateSession / PlatePipeline / VideoMetadata).

Widgets (Viewer, Timeline, Scrubber, TransportControls) stay dumb and
UI-only; this class is where frame numbers get converted to
milliseconds, where probing happens, and where export gets kicked off
on a background thread so the UI never blocks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from ..media.ffmpeg import FFmpegError
from ..media.ffprobe import FFprobeError, probe
from ..models.video_metadata import VideoMetadata
from ..pipeline import PipelineResult, PlatePipeline


class _ExportWorker(QThread):
    """Runs PlatePipeline.run() off the UI thread."""

    progress = Signal(str)
    finished_ok = Signal(object)   # PipelineResult
    failed = Signal(str)

    def __init__(self, pipeline: PlatePipeline, parent: QObject | None = None):
        super().__init__(parent)
        self._pipeline = pipeline

    def run(self) -> None:
        try:
            result = self._pipeline.run(progress=lambda msg: self.progress.emit(msg))
            self.finished_ok.emit(result)
        except (FileNotFoundError, FFprobeError, FFmpegError, ValueError) as exc:
            self.failed.emit(str(exc))


class SessionController(QObject):
    """Owns the current source file, its probed metadata, and the pending
    IN/OUT selection. Converts between frame numbers and milliseconds so
    the rest of the app can think in frames.
    """

    metadataLoaded = Signal(object)   # VideoMetadata
    loadFailed = Signal(str)
    exportProgress = Signal(str)
    exportFinished = Signal(object)   # PipelineResult
    exportFailed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.source_path: Optional[Path] = None
        self.metadata: Optional[VideoMetadata] = None
        self.start_frame: int = 0
        self._worker: Optional[_ExportWorker] = None

    # -- loading ------------------------------------------------------------

    def open_source(self, path: str, start_frame: int = 0) -> None:
        """Probe the file and store its metadata. Emits metadataLoaded on
        success or loadFailed on error.

        Probing a file is fast relative to transcoding, so this runs
        synchronously; if very large/remote files become an issue this
        can move to a QThread the same way export does.
        """
        try:
            metadata = probe(path)
        except (FileNotFoundError, FFprobeError) as exc:
            self.loadFailed.emit(str(exc))
            return

        self.source_path = Path(path)
        self.metadata = metadata
        self.start_frame = start_frame
        self.metadataLoaded.emit(metadata)

    # -- frame/time conversion ------------------------------------------

    def frame_to_ms(self, frame: int) -> int:
        if self.metadata is None:
            return 0
        seconds = (frame - self.start_frame) / self.metadata.fps
        return max(0, round(seconds * 1000))

    def ms_to_frame(self, position_ms: int) -> int:
        if self.metadata is None:
            return self.start_frame
        seconds = position_ms / 1000
        return self.start_frame + round(seconds * self.metadata.fps)

    def total_frames(self) -> int:
        if self.metadata is None or self.metadata.total_frames is None:
            return 0
        return self.metadata.total_frames

    # -- export ---------------------------------------------------------

    def start_export(self, in_frame: int, out_frame: int, options: dict) -> None:
        """Build a PlatePipeline from current source + selection and run it
        on a background QThread. Progress/result arrive via signals.
        """
        if self.source_path is None:
            self.exportFailed.emit("No source file loaded.")
            return

        pipeline = PlatePipeline(
            source=self.source_path,
            in_frame=in_frame,
            out_frame=out_frame,
            start_frame=self.start_frame,
            output_root=options.get("output_root", "./output"),
            proxy_max_width=options.get("proxy_max_width", 1920),
            exr_pixel_format=options.get("exr_pixel_format", "gbrpf32le"),
            skip_exr=options.get("skip_exr", False),
            skip_proxy=options.get("skip_proxy", False),
        )

        self._worker = _ExportWorker(pipeline)
        self._worker.progress.connect(self.exportProgress)
        self._worker.finished_ok.connect(self._on_export_finished)
        self._worker.failed.connect(self.exportFailed)
        self._worker.start()

    def _on_export_finished(self, result: PipelineResult) -> None:
        self.exportFinished.emit(result)
