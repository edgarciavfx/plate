"""MainWindow — the Plate application window.

Wires together the dumb UI widgets (Viewer, Timeline, Scrubber,
TransportControls) via SessionController, which is the only place that
touches PlatePipeline / PlateSession / VideoMetadata. This file itself
should stay wiring-only: widget <-> controller signal connections and
layout, nothing about ffmpeg/ffprobe.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDragMoveEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..config import load as load_config
from ..models.recent_files import RecentFiles
from ..models.shot_queue import ShotQueue
from .export_dialog import ExportDialog
from .scrubber import Scrubber
from .session_controller import SessionController
from .shot_queue_widget import ShotQueueWidget
from .timeline import Timeline
from .transport_controls import TransportControls
from .viewer import Viewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plate")
        self.resize(1280, 800)

        self._config = load_config()
        self._recent_files = RecentFiles.load()

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

        self._queue = ShotQueue.load()
        self._queue_widget = ShotQueueWidget(self)
        dock = QDockWidget("Export Queue", self)
        dock.setWidget(self._queue_widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.setAcceptDrops(True)
        self._build_menu()
        self._build_shortcuts()
        self._wire_signals()

        self.statusBar().showMessage("Open a clip to get started.")
        self._export_action.setEnabled(False)
        self._add_queue_action.setEnabled(False)

    # -- menu -----------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        self._recent_menu = file_menu.addMenu("&Recent Files")
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        self._export_action = QAction("&Export...", self)
        self._export_action.triggered.connect(self._on_export)
        file_menu.addAction(self._export_action)

        self._add_queue_action = QAction("&Add to Queue...", self)
        self._add_queue_action.triggered.connect(self._on_add_to_queue)
        file_menu.addAction(self._add_queue_action)

        file_menu.addSeparator()

        self._run_queue_action = QAction("&Export Queue", self)
        self._run_queue_action.triggered.connect(self._on_run_queue)
        file_menu.addAction(self._run_queue_action)

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        for path in self._recent_files.paths:
            action = QAction(path, self)
            action.triggered.connect(lambda _checked, p=path: self._open_path(p))
            self._recent_menu.addAction(action)
        if not self._recent_files.paths:
            action = QAction("(no recent files)", self)
            action.setEnabled(False)
            self._recent_menu.addAction(action)

    # -- keyboard shortcuts ---------------------------------------------

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._viewer.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._step_frames(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._step_frames(1))
        QShortcut(QKeySequence(Qt.Key.Key_I), self, self._on_set_in)
        QShortcut(QKeySequence(Qt.Key.Key_O), self, self._on_set_out)
        QShortcut(QKeySequence.StandardKey.Undo, self, self._timeline.undo)
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Z), self, self._timeline.undo)

    # -- wiring -----------------------------------------------------------

    def _wire_signals(self) -> None:
        controller = self._controller

        controller.metadataLoaded.connect(self._on_metadata_loaded)
        controller.loadFailed.connect(self._on_load_failed)
        controller.exportProgress.connect(self.statusBar().showMessage)
        controller.exportFinished.connect(self._on_export_finished)
        controller.exportFailed.connect(self._on_export_failed)

        # Queue signals
        controller.queueEntryStarted.connect(self._on_queue_entry_started)
        controller.queueEntryProgress.connect(self._on_queue_entry_progress)
        controller.queueEntryFinished.connect(self._on_queue_entry_finished)
        controller.queueFinished.connect(self._on_queue_finished)

        self._queue_widget.runRequested.connect(self._on_run_queue)
        self._queue_widget.removeRequested.connect(self._on_queue_remove)
        self._queue_widget.clearCompletedRequested.connect(self._on_queue_clear_completed)
        self._queue_widget.openFolderRequested.connect(self._on_open_queue_folder)

        self._viewer.loadError.connect(self._on_viewer_error)
        self._viewer.positionChanged.connect(self._on_position_changed)
        self._viewer.durationChanged.connect(self._scrubber.set_duration)
        self._viewer.fileDropped.connect(self._open_path)

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
        self._open_path(path)

    def _open_path(self, path: str) -> None:
        self.statusBar().showMessage(f"Probing {path}...")
        self._controller.open_source(path)

    # -- drag-drop ---------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
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
        self._add_queue_action.setEnabled(True)
        self._recent_files.record(str(self._controller.source_path))
        self._rebuild_recent_menu()
        self.statusBar().showMessage(
            f"Loaded {self._controller.source_path.name} — "
            f"{metadata.width}x{metadata.height} @ {metadata.fps:.3f}fps, "
            f"{total_frames} frames"
        )

    def _on_load_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Failed to open file", message)
        self.statusBar().showMessage("Failed to open file.")

    def _on_viewer_error(self, message: str) -> None:
        QMessageBox.critical(self, "Playback error", message)
        self.statusBar().showMessage("Playback error.")

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
        new_frame = max(0, min(current_frame + delta, self._controller.total_frames() - 1))
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

        export_defaults = self._config.get("export", {}) if self._config else {}
        dialog = ExportDialog(parent=self, defaults=export_defaults)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return

        self._export_action.setEnabled(False)
        self._controller.start_export(in_frame, out_frame, dialog.options())

    def _on_export_finished(self, result) -> None:
        self._export_action.setEnabled(True)
        output_dir = result.session.output_dir
        self.statusBar().showMessage(
            f"Done. Manifest: {result.manifest_path}  [Ctrl+O to open folder]"
        )
        self._open_folder_action = QAction("Open Containing Folder...", self)
        self._open_folder_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))
        )
        self._open_folder_action.setShortcut(QKeySequence.StandardKey.Open)
        self.addAction(self._open_folder_action)

    def _on_export_failed(self, message: str) -> None:
        self._export_action.setEnabled(True)
        QMessageBox.critical(self, "Export failed", message)
        self.statusBar().showMessage("Export failed.")

    # -- add to queue -------------------------------------------------------

    def _on_add_to_queue(self) -> None:
        in_frame = self._timeline.in_frame()
        out_frame = self._timeline.out_frame()
        if in_frame is None or out_frame is None:
            QMessageBox.warning(self, "No selection", "Set an IN and OUT frame first.")
            return

        export_defaults = self._config.get("export", {}) if self._config else {}
        dialog = ExportDialog(mode="add_to_queue", parent=self, defaults=export_defaults)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return

        source = str(self._controller.source_path)
        options = dialog.options()
        entry = self._controller.add_to_queue(source, in_frame, out_frame, options)
        self._queue.add(entry)
        self._queue_widget.load_queue(self._queue)
        self.statusBar().showMessage(f"Added {Path(source).name} to queue ({len(self._queue)} total).")

    # -- queue operations ---------------------------------------------------

    def _on_queue_remove(self, index: int) -> None:
        if self._controller.is_queue_running():
            return
        self._queue.remove(index)
        self._queue_widget.load_queue(self._queue)

    def _on_open_queue_folder(self, index: int) -> None:
        if 0 <= index < len(self._queue.entries):
            entry = self._queue.entries[index]
            if entry.manifest_path:
                folder = Path(entry.manifest_path).parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _on_queue_clear_completed(self) -> None:
        self._queue.clear_completed()
        self._queue_widget.load_queue(self._queue)

    def _on_run_queue(self) -> None:
        if self._controller.is_queue_running():
            return
        pending = self._queue.pending_entries()
        if not pending:
            self.statusBar().showMessage("Queue is empty.")
            return

        self._queue_widget.set_running(True)
        self._run_queue_action.setEnabled(False)
        self._add_queue_action.setEnabled(False)
        self._export_action.setEnabled(False)
        self.statusBar().showMessage(f"Exporting {len(pending)} shot(s) from queue…")
        self._controller.run_queue(self._queue)

    def _on_queue_entry_started(self, index: int) -> None:
        self._queue_widget.on_entry_changed(index)

    def _on_queue_entry_progress(self, index: int, message: str) -> None:
        self._queue_widget.on_entry_changed(index)
        source = Path(self._queue[index].source).name
        self.statusBar().showMessage(f"[{source}] {message}")

    def _on_queue_entry_finished(self, index: int, result: object, error: str | None) -> None:
        self._queue_widget.on_entry_changed(index)

    def _on_queue_finished(self) -> None:
        self._queue.save()
        self._queue_widget.load_queue(self._queue)
        self._queue_widget.set_running(False)
        self._run_queue_action.setEnabled(True)
        self._add_queue_action.setEnabled(True)
        self._export_action.setEnabled(self._controller.metadata is not None)

        done = sum(1 for e in self._queue.entries if e.status == "done")
        failed = sum(1 for e in self._queue.entries if e.status == "failed")
        self.statusBar().showMessage(f"Queue finished: {done} succeeded, {failed} failed.")
