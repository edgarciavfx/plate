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

from ..color import ColorTransform
from ..media.ffmpeg import FFmpegError
from ..media.ffprobe import FFprobeError, probe
from ..models.shot_queue import QueueEntry, ShotQueue
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
            result = self._pipeline.run(progress=lambda msg, _pct=None: self.progress.emit(msg))
            self.finished_ok.emit(result)
        except (FileNotFoundError, FFprobeError, FFmpegError, ValueError) as exc:
            self.failed.emit(str(exc))


class _QueueWorker(QThread):
    """Processes all pending entries in a ShotQueue sequentially."""

    entryStarted = Signal(int)        # index
    entryProgress = Signal(int, str)  # index, message
    entryFinished = Signal(int, object, str)  # index, PipelineResult | None, error | None
    queueFinished = Signal()

    def __init__(self, queue: ShotQueue, parent: QObject | None = None):
        super().__init__(parent)
        self._queue = queue

    def run(self) -> None:
        for idx, entry in enumerate(self._queue.entries):
            if not entry.is_pending():
                continue

            entry.status = "processing"
            self.entryStarted.emit(idx)

            try:
                color_transform = self._resolve_color(entry)
                pipeline = PlatePipeline(
                    source=entry.source,
                    in_frame=entry.in_frame,
                    out_frame=entry.out_frame,
                    start_frame=entry.start_frame,
                    output_root=entry.output_root,
                    proxy_max_width=entry.proxy_max_width,
                    exr_pixel_format=entry.exr_pixel_format,
                    exr_compression=entry.exr_compression,
                    frame_padding=entry.frame_padding,
                    skip_exr=entry.skip_exr,
                    skip_proxy=entry.skip_proxy,
                    color_transform=color_transform,
                    burn_in=entry.burn_in,
                )
                result = pipeline.run(
                    progress=lambda msg, _pct=None, _idx=idx: self.entryProgress.emit(_idx, msg)
                )
                entry.status = "done"
                entry.error = None
                entry.manifest_path = str(result.manifest_path)
                self.entryFinished.emit(idx, result, None)

            except Exception as exc:
                entry.status = "failed"
                entry.error = str(exc)
                self.entryFinished.emit(idx, None, str(exc))

        self._queue.save()
        self.queueFinished.emit()

    @staticmethod
    def _resolve_color(entry: QueueEntry) -> ColorTransform:
        if entry.color_mode == "lut" and entry.lut_path:
            return ColorTransform(lut_path=Path(entry.lut_path))
        if entry.color_mode == "ocio" and entry.ocio_config:
            return ColorTransform(
                ocio_config=Path(entry.ocio_config),
                src_colorspace=entry.ocio_src,
                dst_colorspace=entry.ocio_dst,
            )
        return ColorTransform()


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

    queueEntryStarted = Signal(int)
    queueEntryProgress = Signal(int, str)
    queueEntryFinished = Signal(int, object, str)  # index, PipelineResult | None, error | None
    queueFinished = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.source_path: Optional[Path] = None
        self.metadata: Optional[VideoMetadata] = None
        self.start_frame: int = 0
        self._worker: Optional[_ExportWorker] = None
        self._queue_worker: Optional[_QueueWorker] = None
        self._queue: Optional[ShotQueue] = None

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

        color_transform = self._color_transform_from_options(options)
        if color_transform is None:
            self.exportFailed.emit(
                "Invalid color transform options. Check your LUT/OCIO settings."
            )
            return

        pipeline = PlatePipeline(
            source=self.source_path,
            in_frame=in_frame,
            out_frame=out_frame,
            start_frame=self.start_frame,
            output_root=options.get("output_root", "./output"),
            proxy_max_width=options.get("proxy_max_width", 1920),
            exr_pixel_format=options.get("exr_pixel_format", "gbrpf32le"),
            exr_compression=options.get("exr_compression", "zip1"),
            frame_padding=options.get("frame_padding", 6),
            skip_exr=options.get("skip_exr", False),
            skip_proxy=options.get("skip_proxy", False),
            color_transform=color_transform,
            burn_in=options.get("burn_in"),
        )

        self._worker = _ExportWorker(pipeline)
        self._worker.progress.connect(self.exportProgress)
        self._worker.finished_ok.connect(self._on_export_finished)
        self._worker.failed.connect(self.exportFailed)
        self._worker.start()

    def _color_transform_from_options(self, options: dict) -> ColorTransform | None:
        mode = options.get("color_mode", "none")
        try:
            if mode == "lut":
                return ColorTransform.from_options(lut_path=options.get("lut_path"))
            if mode == "ocio":
                return ColorTransform.from_options(
                    ocio_config=options.get("ocio_config"),
                    ocio_src=options.get("ocio_src"),
                    ocio_dst=options.get("ocio_dst"),
                )
            return ColorTransform()
        except ValueError:
            return None

    def _on_export_finished(self, result: PipelineResult) -> None:
        self.exportFinished.emit(result)

    # -- queue -------------------------------------------------------------

    def add_to_queue(self, source: str, in_frame: int, out_frame: int, options: dict) -> QueueEntry:
        entry = QueueEntry(
            source=source,
            in_frame=in_frame,
            out_frame=out_frame,
            start_frame=options.get("start_frame", self.start_frame),
            output_root=options.get("output_root", "./output"),
            proxy_max_width=options.get("proxy_max_width", 1920),
            exr_pixel_format=options.get("exr_pixel_format", "gbrpf32le"),
            exr_compression=options.get("exr_compression", "zip1"),
            frame_padding=options.get("frame_padding", 6),
            skip_exr=options.get("skip_exr", False),
            skip_proxy=options.get("skip_proxy", False),
            color_mode=options.get("color_mode", "none"),
            lut_path=options.get("lut_path"),
            ocio_config=options.get("ocio_config"),
            ocio_src=options.get("ocio_src"),
            ocio_dst=options.get("ocio_dst"),
            burn_in=options.get("burn_in"),
        )
        return entry

    def is_queue_running(self) -> bool:
        return self._queue_worker is not None and self._queue_worker.isRunning()

    def run_queue(self, queue: ShotQueue) -> None:
        if self.is_queue_running():
            return
        self._queue = queue
        self._queue_worker = _QueueWorker(queue)
        self._queue_worker.entryStarted.connect(self.queueEntryStarted)
        self._queue_worker.entryProgress.connect(self._on_queue_entry_progress)
        self._queue_worker.entryFinished.connect(self._on_queue_entry_finished)
        self._queue_worker.queueFinished.connect(self._on_queue_finished)
        self._queue_worker.start()

    def _on_queue_entry_progress(self, index: int, message: str) -> None:
        self.queueEntryProgress.emit(index, message)

    def _on_queue_entry_finished(self, index: int, result: object, error: str | None) -> None:
        self.queueEntryFinished.emit(index, result, error)

    def _on_queue_finished(self) -> None:
        self.queueFinished.emit()
