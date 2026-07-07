"""MainWindow — the Plate application window.

Wires together the dumb UI widgets (Viewer, Timeline, Scrubber,
TransportControls) via SessionController, which is the only place that
touches PlatePipeline / PlateSession / VideoMetadata. This file itself
should stay wiring-only: widget <-> controller signal connections and
layout, nothing about ffmpeg/ffprobe.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QAction

from .export_dialog import ExportDialog
from .scrubber import Scrubber
from .session_controller import SessionController
from .timeline import Timeline
from .transport_controls import TransportControls
from .viewer import Viewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plate")
        self.resize(1280, 800)

        self._controller = SessionController(self)

        self._viewer = Viewer(self)
        self._scrubber = Scrubber(self)
        self._timeline = Timeline(self)
        self._transport = TransportControls(self)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self._viewer, stretch=1)
        layout.addWidget(self._scrubber)
        layout.addWidget(self._timeline)
        layout.addWidget(self._transport)
        self.setCentralWidget(central)

        self._build_menu()
        self._wire_signals()

        self.statusBar().showMessage("Open a clip to get started.")
        self._export_action.setEnabled(False)

    # -- menu -----------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        self._export_action = QAction("&Export...", self)
        self._export_action.triggered.connect(self._on_export)
        file_menu.addAction(self._export_action)

    # -- wiring -----------------------------------------------------------

    def _wire_signals(self) -> None:
        controller = self._controller

        controller.metadataLoaded.connect(self._on_metadata_loaded)
        controller.loadFailed.connect(self._on_load_failed)
        controller.exportProgress.connect(self.statusBar().showMessage)
        controller.exportFinished.connect(self._on_export_finished)
        controller.exportFailed.connect(self._on_export_failed)

        self._viewer.positionChanged.connect(self._on_position_changed)
        self._viewer.durationChanged.connect(self._scrubber.set_duration)

        self._scrubber.seekRequested.connect(self._viewer.seek_ms)
        self._timeline.seekRequested.connect(self._on_timeline_seek)

        self._transport.playPauseClicked.connect(self._viewer.toggle_play_pause)
        self._transport.stepBackClicked.connect(lambda: self._step_frames(-1))
        self._transport.stepForwardClicked.connect(lambda: self._step_frames(1))
        self._transport.setInClicked.connect(self._on_set_in)
        self._transport.setOutClicked.connect(self._on_set_out)

        self._viewer.playbackStateChanged.connect(
            lambda _state: self._transport.set_playing(self._viewer.is_playing())
        )

    # -- open -------------------------------------------------------------

    def _on_open(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Open Footage", "", "Video Files (*.mov *.mp4 *.mxf *.avi);;All Files (*)"
        )
        if not path:
            return
        self.statusBar().showMessage(f"Probing {path}...")
        self._controller.open_source(path)

    def _on_metadata_loaded(self, metadata) -> None:
        self._viewer.load(str(self._controller.source_path))
        total_frames = self._controller.total_frames()
        start_frame = self._controller.start_frame
        self._timeline.set_range(start_frame, total_frames)
        self._export_action.setEnabled(True)
        self.statusBar().showMessage(
            f"Loaded {self._controller.source_path.name} — "
            f"{metadata.width}x{metadata.height} @ {metadata.fps:.3f}fps, "
            f"{total_frames} frames"
        )

    def _on_load_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Failed to open file", message)
        self.statusBar().showMessage("Failed to open file.")

    # -- playback / scrubbing --------------------------------------------

    def _on_position_changed(self, position_ms: int) -> None:
        self._scrubber.set_position(position_ms)
        current_frame = self._controller.ms_to_frame(position_ms)
        self._timeline.set_current_frame(current_frame)
        self._transport.set_frame_label(
            current_frame,
            self._timeline.in_frame() or 0,
            self._timeline.out_frame() or 0,
        )

    def _on_timeline_seek(self, frame: int) -> None:
        self._viewer.seek_ms(self._controller.frame_to_ms(frame))

    def _step_frames(self, delta: int) -> None:
        if self._controller.metadata is None:
            return
        current_frame = self._controller.ms_to_frame(self._viewer.position_ms())
        new_frame = current_frame + delta
        self._viewer.seek_ms(self._controller.frame_to_ms(new_frame))

    def _on_set_in(self) -> None:
        current_frame = self._controller.ms_to_frame(self._viewer.position_ms())
        self._timeline.set_in_frame(current_frame)

    def _on_set_out(self) -> None:
        current_frame = self._controller.ms_to_frame(self._viewer.position_ms())
        self._timeline.set_out_frame(current_frame)

    # -- export ------------------------------------------------------------

    def _on_export(self) -> None:
        in_frame = self._timeline.in_frame()
        out_frame = self._timeline.out_frame()
        if in_frame is None or out_frame is None:
            QMessageBox.warning(self, "No selection", "Set an IN and OUT frame first.")
            return

        dialog = ExportDialog(parent=self)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return

        self._export_action.setEnabled(False)
        self._controller.start_export(in_frame, out_frame, dialog.options())

    def _on_export_finished(self, result) -> None:
        self._export_action.setEnabled(True)
        self.statusBar().showMessage(f"Done. Manifest: {result.manifest_path}")

    def _on_export_failed(self, message: str) -> None:
        self._export_action.setEnabled(True)
        QMessageBox.critical(self, "Export failed", message)
        self.statusBar().showMessage("Export failed.")
