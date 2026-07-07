"""ExportDialog — collects export options and hands them back as a plain
dict. It knows nothing about PlatePipeline directly; SessionController
takes the dict and builds/runs the pipeline.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget,
)


class ExportDialog(QDialog):
    def __init__(self, default_output_dir: str = "./output", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Export Shot")

        self._output_dir_edit = QLineEdit(default_output_dir)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_dir)

        output_row = QHBoxLayout()
        output_row.addWidget(self._output_dir_edit)
        output_row.addWidget(browse_button)
        output_row_widget = QWidget()
        output_row_widget.setLayout(output_row)

        self._proxy_width_spin = QSpinBox()
        self._proxy_width_spin.setRange(320, 7680)
        self._proxy_width_spin.setValue(1920)
        self._proxy_width_spin.setSingleStep(64)

        self._pixfmt_combo = QComboBox()
        self._pixfmt_combo.addItems(["gbrpf32le", "gbrp16le", "rgb48le"])

        self._skip_exr_check = QCheckBox("Skip EXR sequence")
        self._skip_proxy_check = QCheckBox("Skip proxy")

        form = QFormLayout()
        form.addRow("Output directory:", output_row_widget)
        form.addRow("Proxy max width:", self._proxy_width_spin)
        form.addRow("EXR pixel format:", self._pixfmt_combo)
        form.addRow(self._skip_exr_check)
        form.addRow(self._skip_proxy_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if directory:
            self._output_dir_edit.setText(directory)

    def options(self) -> dict:
        """Call after exec() returns Accepted."""
        return {
            "output_root": self._output_dir_edit.text(),
            "proxy_max_width": self._proxy_width_spin.value(),
            "exr_pixel_format": self._pixfmt_combo.currentText(),
            "skip_exr": self._skip_exr_check.isChecked(),
            "skip_proxy": self._skip_proxy_check.isChecked(),
        }
