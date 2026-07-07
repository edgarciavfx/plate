"""Timeline — the visual frame-range selector.

This is the one genuinely differentiating widget in Plate. It draws a
frame ruler across the clip's full length, shows the current playhead,
and shows draggable IN/OUT markers. Everything else in the app exists
to feed this widget accurate frame numbers, and to read the range back
out of it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QMouseEvent, QPaintEvent
from PySide6.QtWidgets import QWidget

_HANDLE_WIDTH = 8
_RULER_HEIGHT = 36


class Timeline(QWidget):
    """A frame-indexed ruler with a playhead and draggable IN/OUT handles.

    All frame numbers are in "source" numbering (i.e. offset by
    start_frame), matching what the artist sees in other tools.
    """

    seekRequested = Signal(int)     # frame number
    inFrameChanged = Signal(int)    # frame number
    outFrameChanged = Signal(int)   # frame number

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(_RULER_HEIGHT + 20)
        self.setMouseTracking(True)

        self._start_frame = 0
        self._total_frames = 0
        self._current_frame = 0
        self._in_frame: int | None = None
        self._out_frame: int | None = None

        self._dragging: str | None = None  # "in", "out", "playhead", or None

    # -- configuration ------------------------------------------------------

    def set_range(self, start_frame: int, total_frames: int) -> None:
        """Configure the clip's full frame range (call after probing)."""
        self._start_frame = start_frame
        self._total_frames = max(total_frames, 1)
        self._in_frame = start_frame
        self._out_frame = start_frame + self._total_frames - 1
        self._current_frame = start_frame
        self.update()

    def set_current_frame(self, frame: int) -> None:
        self._current_frame = frame
        self.update()

    def in_frame(self) -> int | None:
        return self._in_frame

    def out_frame(self) -> int | None:
        return self._out_frame

    def set_in_frame(self, frame: int) -> None:
        self._in_frame = self._clamp(frame)
        if self._out_frame is not None and self._in_frame > self._out_frame:
            self._out_frame = self._in_frame
        self.inFrameChanged.emit(self._in_frame)
        self.update()

    def set_out_frame(self, frame: int) -> None:
        self._out_frame = self._clamp(frame)
        if self._in_frame is not None and self._out_frame < self._in_frame:
            self._in_frame = self._out_frame
        self.outFrameChanged.emit(self._out_frame)
        self.update()

    # -- helpers --------------------------------------------------------

    def _clamp(self, frame: int) -> int:
        last_frame = self._start_frame + self._total_frames - 1
        return max(self._start_frame, min(frame, last_frame))

    def _frame_to_x(self, frame: int) -> int:
        if self._total_frames <= 1:
            return 0
        ratio = (frame - self._start_frame) / (self._total_frames - 1)
        return int(ratio * self.width())

    def _x_to_frame(self, x: int) -> int:
        if self.width() <= 0:
            return self._start_frame
        ratio = max(0.0, min(1.0, x / self.width()))
        frame = self._start_frame + round(ratio * (self._total_frames - 1))
        return self._clamp(frame)

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ruler_rect = QRect(0, 0, self.width(), _RULER_HEIGHT)
        painter.fillRect(ruler_rect, QColor("#1e1e1e"))

        if self._total_frames <= 1:
            painter.end()
            return

        # Selected IN/OUT range highlight
        if self._in_frame is not None and self._out_frame is not None:
            x_in = self._frame_to_x(self._in_frame)
            x_out = self._frame_to_x(self._out_frame)
            painter.fillRect(
                QRect(x_in, 0, max(x_out - x_in, 1), _RULER_HEIGHT),
                QColor("#2d6a4f"),
            )

        # Tick marks every ~10% of the ruler
        painter.setPen(QColor("#555555"))
        tick_count = 10
        for i in range(tick_count + 1):
            x = int(i / tick_count * self.width())
            painter.drawLine(x, _RULER_HEIGHT - 6, x, _RULER_HEIGHT)

        # Playhead
        x_playhead = self._frame_to_x(self._current_frame)
        painter.setPen(QColor("#e63946"))
        painter.drawLine(x_playhead, 0, x_playhead, self.height())

        # IN/OUT handles
        if self._in_frame is not None:
            self._draw_handle(painter, self._frame_to_x(self._in_frame), QColor("#40916c"))
        if self._out_frame is not None:
            self._draw_handle(painter, self._frame_to_x(self._out_frame), QColor("#d62828"))

        painter.end()

    def _draw_handle(self, painter: QPainter, x: int, color: QColor) -> None:
        painter.fillRect(
            QRect(x - _HANDLE_WIDTH // 2, 0, _HANDLE_WIDTH, _RULER_HEIGHT),
            color,
        )

    # -- mouse interaction ------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        x = int(event.position().x())
        if self._near_handle(x, self._in_frame):
            self._dragging = "in"
        elif self._near_handle(x, self._out_frame):
            self._dragging = "out"
        else:
            self._dragging = "playhead"
            frame = self._x_to_frame(x)
            self.set_current_frame(frame)
            self.seekRequested.emit(frame)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging is None:
            return
        x = int(event.position().x())
        frame = self._x_to_frame(x)
        if self._dragging == "in":
            self.set_in_frame(frame)
        elif self._dragging == "out":
            self.set_out_frame(frame)
        elif self._dragging == "playhead":
            self.set_current_frame(frame)
            self.seekRequested.emit(frame)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = None

    def _near_handle(self, x: int, frame: int | None, tolerance: int = 6) -> bool:
        if frame is None:
            return False
        return abs(self._frame_to_x(frame) - x) <= tolerance
