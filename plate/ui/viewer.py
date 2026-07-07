"""Viewer — the video display + playback engine.

This is a thin wrapper around Qt Multimedia. It knows nothing about
frames, IN/OUT points, or export — it only plays a file and reports
position/duration in milliseconds. Frame-accurate concepts live in
SessionController, which sits above this.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout


class Viewer(QWidget):
    """Displays video and exposes simple, time-based playback controls."""

    positionChanged = Signal(int)   # milliseconds
    durationChanged = Signal(int)   # milliseconds
    playbackStateChanged = Signal(QMediaPlayer.PlaybackState)
    loadError = Signal(str)
    fileDropped = Signal(str)       # local file path

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._video_widget = QVideoWidget(self)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._kicked = False

        self._player.setVideoOutput(self._video_widget)
        self._player.setAudioOutput(self._audio_output)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self.playbackStateChanged)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._video_widget)

        self._video_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAcceptDrops(True)

    # -- drag-drop ---------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.fileDropped.emit(path)

    # -- internal relays --------------------------------------------------

    def _on_position_changed(self, position: int) -> None:
        self.positionChanged.emit(int(position))

    def _on_duration_changed(self, duration: int) -> None:
        self.durationChanged.emit(int(duration))

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.loadError.emit(error_string)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            self._player.setPosition(0)
            if not self._kicked:
                self._kicked = True
                QTimer.singleShot(100, self._player.pause)
                self._player.play()

    # -- source ---------------------------------------------------------

    def load(self, path: str) -> None:
        self._kicked = False
        self._player.setSource(QUrl.fromLocalFile(path))

    # -- transport --------------------------------------------------------

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def toggle_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def seek_ms(self, position_ms: int) -> None:
        self._player.setPosition(position_ms)

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # -- state ------------------------------------------------------------

    def position_ms(self) -> int:
        return self._player.position()

    def duration_ms(self) -> int:
        return self._player.duration()
