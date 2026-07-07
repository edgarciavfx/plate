"""ProgressDialog — a non-modal floating window that shows progress
of an export or queue run so the user knows something is happening.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressDialog(QDialog):
    cancelled = Signal()

    def __init__(self, title: str = "Processing", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("progressDialog")
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setFixedSize(420, 130)
        self.setModal(False)

        self._message_label = QLabel("Starting...")
        self._message_label.setObjectName("progressMessage")
        self._message_label.setWordWrap(True)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("progressBar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setObjectName("progressCancelButton")
        self._cancel_button.clicked.connect(self._on_cancel)

        msg_layout = QHBoxLayout()
        msg_layout.addWidget(self._message_label, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addLayout(msg_layout)
        layout.addWidget(self._progress_bar)
        layout.addLayout(btn_layout)

    def set_progress(self, message: str, percent: int = 0) -> None:
        self._message_label.setText(message)
        self._progress_bar.setValue(percent)

    def _on_cancel(self) -> None:
        self._cancel_button.setEnabled(False)
        self._cancel_button.setText("Cancelling…")
        self.cancelled.emit()
