"""Scrubber — a smooth, time-based scrub bar for playback.

This is deliberately separate from Timeline: Timeline is the
frame-accurate IN/OUT selector (frame numbers, source numbering),
while Scrubber is a lightweight millisecond-resolution slider for
quickly scrubbing through playback. SessionController keeps both in
sync with the Viewer's actual position.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSlider, QWidget


class Scrubber(QSlider):
    """A horizontal slider representing playback position in milliseconds.

    Emits seekRequested(ms) only on user-driven interaction (press/drag/
    click) — programmatic position updates from the Viewer should call
    set_position() instead, which does not re-emit the signal.
    """

    seekRequested = Signal(int)  # milliseconds

    def __init__(self, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._user_driven = True

        self.setRange(0, 0)
        self.sliderMoved.connect(self._on_user_seek)
        self.sliderPressed.connect(self._on_user_press)

    def set_duration(self, duration_ms: int) -> None:
        self.setRange(0, max(duration_ms, 0))

    def set_position(self, position_ms: int) -> None:
        """Update the slider from the Viewer without re-triggering a seek."""
        self._user_driven = False
        self.setValue(position_ms)
        self._user_driven = True

    def _on_user_press(self) -> None:
        self.seekRequested.emit(self.value())

    def _on_user_seek(self, value: int) -> None:
        if self._user_driven:
            self.seekRequested.emit(value)
