"""TransportControls — the button row: Play/Pause, step ±1 frame,
Set IN, Set OUT, plus a frame-number readout.

Like every other widget here, this owns no media logic — it only emits
signals that SessionController listens to.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel


class TransportControls(QWidget):
    playPauseClicked = Signal()
    stepBackClicked = Signal()
    stepForwardClicked = Signal()
    setInClicked = Signal()
    setOutClicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._play_button = QPushButton("Play")
        self._step_back_button = QPushButton("<< Step")
        self._step_forward_button = QPushButton("Step >>")
        self._set_in_button = QPushButton("Set IN")
        self._set_out_button = QPushButton("Set OUT")
        self._frame_label = QLabel("Frame: -")

        self._play_button.clicked.connect(self.playPauseClicked)
        self._step_back_button.clicked.connect(self.stepBackClicked)
        self._step_forward_button.clicked.connect(self.stepForwardClicked)
        self._set_in_button.clicked.connect(self.setInClicked)
        self._set_out_button.clicked.connect(self.setOutClicked)

        layout = QHBoxLayout(self)
        layout.addWidget(self._step_back_button)
        layout.addWidget(self._play_button)
        layout.addWidget(self._step_forward_button)
        layout.addStretch()
        layout.addWidget(self._set_in_button)
        layout.addWidget(self._set_out_button)
        layout.addStretch()
        layout.addWidget(self._frame_label)

    def set_playing(self, is_playing: bool) -> None:
        self._play_button.setText("Pause" if is_playing else "Play")

    def set_frame_label(self, current: int, in_frame: int, out_frame: int) -> None:
        self._frame_label.setText(
            f"Frame: {current}   [IN {in_frame}  OUT {out_frame}]"
        )
