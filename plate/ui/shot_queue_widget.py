"""ShotQueueWidget — displays the persistent shot queue and lets the user
remove entries, clear completed ones, and start processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models.shot_queue import ShotQueue


_STATUS_LABELS = {
    "pending": "Pending",
    "processing": "Processing…",
    "done": "Done",
    "failed": "Failed",
}


class ShotQueueWidget(QGroupBox):
    runRequested = Signal()
    removeRequested = Signal(list)
    clearCompletedRequested = Signal()
    entryDoubleClicked = Signal(int)
    openFolderRequested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Export Queue", parent)
        self._queue: ShotQueue = ShotQueue()

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Source", "Range", "Status"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().hide()
        self._table.itemSelectionChanged.connect(self._update_button_state)
        self._table.cellDoubleClicked.connect(self._on_double_click)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._on_remove)

        self._clear_btn = QPushButton("Clear Completed")
        self._clear_btn.clicked.connect(self.clearCompletedRequested)

        self._run_btn = QPushButton("Run Queue")
        self._run_btn.clicked.connect(self.runRequested)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._remove_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._run_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(btn_layout)

    # -- data ---------------------------------------------------------------

    def load_queue(self, queue: ShotQueue) -> None:
        self._queue = queue
        self._refresh()

    def _refresh(self) -> None:
        self._table.setRowCount(len(self._queue.entries))
        for i, entry in enumerate(self._queue.entries):
            source = Path(entry.source).name

            self._table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._table.setItem(i, 1, QTableWidgetItem(source))
            self._table.setItem(
                i, 2, QTableWidgetItem(f"{entry.in_frame} – {entry.out_frame}")
            )

            status_item = QTableWidgetItem(_STATUS_LABELS.get(entry.status, entry.status))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 3, status_item)

        self._update_button_state()

    def _update_button_state(self) -> None:
        has_pending = any(e.is_pending() for e in self._queue.entries)
        has_selection = len(self._table.selectedIndexes()) > 0
        has_completed = any(e.status in ("done", "failed") for e in self._queue.entries)

        self._run_btn.setEnabled(has_pending)
        self._remove_btn.setEnabled(has_selection)
        self._clear_btn.setEnabled(has_completed)

    # -- slots --------------------------------------------------------------

    def _on_remove(self) -> None:
        rows = sorted(set(idx.row() for idx in self._table.selectedIndexes()), reverse=True)
        if rows:
            self.removeRequested.emit(rows)

    def _on_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._queue.entries):
            entry = self._queue.entries[row]
            if entry.status == "done":
                self.openFolderRequested.emit(row)
        self.entryDoubleClicked.emit(row)

    def on_entry_changed(self, index: int) -> None:
        self._refresh()

    def set_running(self, running: bool) -> None:
        has_pending = any(e.is_pending() for e in self._queue.entries)
        self._run_btn.setEnabled(not running and has_pending)
        self._run_btn.setText("Exporting…" if running else "Run Queue")
        self._remove_btn.setEnabled(not running)
        self._clear_btn.setEnabled(not running)
