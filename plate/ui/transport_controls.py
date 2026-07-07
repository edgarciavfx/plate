"""TransportControls — the button row: Play/Pause, step ±1 frame,
Set IN, Set OUT, plus a frame-number readout.

Like every other widget here, this owns no media logic — it only emits
signals that SessionController listens to.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from .icons import load_svg_icon

_ICON_SIZE = 16


class TransportControls(QWidget):
    playPauseClicked = Signal()
    stepBackClicked = Signal()
    stepForwardClicked = Signal()
    setInClicked = Signal()
    setOutClicked = Signal()
    loopToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._play_button = QPushButton()
        self._play_button.setObjectName("playButton")
        self._play_icon = load_svg_icon("play", _ICON_SIZE)
        self._pause_icon = load_svg_icon("pause", _ICON_SIZE)
        self._play_button.setIcon(self._play_icon)
        self._play_button.setToolTip("Play / Pause (Space)")

        self._step_back_button = QPushButton()
        self._step_back_button.setIcon(load_svg_icon("skip_back", _ICON_SIZE))
        self._step_back_button.setToolTip("Step back one frame (←)")

        self._step_forward_button = QPushButton()
        self._step_forward_button.setIcon(load_svg_icon("skip_forward", _ICON_SIZE))
        self._step_forward_button.setToolTip("Step forward one frame (→)")

        self._set_in_button = QPushButton()
        self._set_in_button.setObjectName("setInButton")
        self._set_in_button.setIcon(load_svg_icon("mark_in", _ICON_SIZE))
        self._set_in_button.setToolTip("Set IN frame (I)")

        self._set_out_button = QPushButton()
        self._set_out_button.setObjectName("setOutButton")
        self._set_out_button.setIcon(load_svg_icon("mark_out", _ICON_SIZE))
        self._set_out_button.setToolTip("Set OUT frame (O)")

        self._loop_button = QPushButton()
        self._loop_button.setObjectName("loopButton")
        self._loop_button.setIcon(load_svg_icon("loop", _ICON_SIZE))
        self._loop_button.setCheckable(True)
        self._loop_button.setChecked(True)
        self._loop_button.setToolTip("Loop IN→OUT (toggle)")

        self._frame_label = QLabel("Frame: —")
        self._frame_label.setObjectName("frameLabel")

        self._play_button.clicked.connect(self.playPauseClicked)
        self._step_back_button.clicked.connect(self.stepBackClicked)
        self._step_forward_button.clicked.connect(self.stepForwardClicked)
        self._set_in_button.clicked.connect(self.setInClicked)
        self._set_out_button.clicked.connect(self.setOutClicked)
        self._loop_button.toggled.connect(self.loopToggled)

        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.addStretch()
        layout.addWidget(self._set_in_button)
        layout.addWidget(self._step_back_button)
        layout.addWidget(self._play_button)
        layout.addWidget(self._step_forward_button)
        layout.addWidget(self._set_out_button)
        layout.addStretch()
        layout.addWidget(self._loop_button)
        layout.addWidget(self._frame_label)

    def set_playing(self, is_playing: bool) -> None:
        self._play_button.setIcon(self._pause_icon if is_playing else self._play_icon)
        self._play_button.setToolTip("Pause (Space)" if is_playing else "Play (Space)")

    def set_frame_label(self, current: int, in_frame: int, out_frame: int) -> None:
        self._frame_label.setText(
            f"Frame: {current}   IN {in_frame}  OUT {out_frame}"
        )
