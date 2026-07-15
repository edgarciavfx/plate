"""ExportDialog — collects export options and hands them back as a plain
dict. It knows nothing about PlatePipeline directly; SessionController
takes the dict and builds/runs the pipeline.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget,
)

from ..presets import all_presets, resolve_preset


class ExportDialog(QDialog):
    def __init__(self, default_output_dir: str = "./output", mode: str = "export",
                 defaults: dict | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._defaults = defaults or {}
        self._base_defaults = dict(self._defaults)
        self._suppress_preset = False
        title = "Add to Queue" if mode == "add_to_queue" else "Export Shot"
        self.setWindowTitle(title)

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("Custom")
        self._preset_names: list[str] = []
        for name in all_presets():
            self._preset_combo.addItem(name)
            self._preset_names.append(name)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        self._output_dir_edit = QLineEdit(
            self._defaults.get("output_root", default_output_dir)
        )
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_dir)

        output_row = QHBoxLayout()
        output_row.addWidget(self._output_dir_edit)
        output_row.addWidget(browse_button)
        output_row_widget = QWidget()
        output_row_widget.setLayout(output_row)

        self._shot_edit = QLineEdit(self._defaults.get("shot") or "")
        self._shot_edit.setPlaceholderText(
            "e.g. img01_env — empty keeps the classic layout"
        )
        self._shot_edit.textChanged.connect(self._on_shot_changed)

        self._shot_version_spin = QSpinBox()
        self._shot_version_spin.setRange(0, 999)
        self._shot_version_spin.setSpecialValueText("auto")
        self._shot_version_spin.setValue(self._defaults.get("shot_version") or 0)

        self._proxy_width_spin = QSpinBox()
        self._proxy_width_spin.setRange(320, 7680)
        self._proxy_width_spin.setValue(self._defaults.get("proxy_max_width", 1920))
        self._proxy_width_spin.setSingleStep(64)

        self._pixfmt_combo = QComboBox()
        self._pixfmt_combo.addItems(["gbrpf32le", "gbrp16le", "rgb48le"])
        default_pixfmt = self._defaults.get("exr_pixel_format", "gbrpf32le")
        idx = self._pixfmt_combo.findText(default_pixfmt)
        if idx >= 0:
            self._pixfmt_combo.setCurrentIndex(idx)

        self._exr_codec_combo = QComboBox()
        self._exr_codec_combo.addItems(["none", "rle", "zip1", "zip16"])
        default_codec = self._defaults.get("exr_compression", "zip1")
        idx = self._exr_codec_combo.findText(default_codec)
        if idx >= 0:
            self._exr_codec_combo.setCurrentIndex(idx)

        self._frame_padding_spin = QSpinBox()
        self._frame_padding_spin.setRange(1, 10)
        self._frame_padding_spin.setValue(self._defaults.get("frame_padding", 6))

        self._skip_exr_check = QCheckBox("Skip EXR sequence")
        self._skip_proxy_check = QCheckBox("Skip proxy")
        self._nuke_script_check = QCheckBox("Generate Nuke script (.nk)")

        # -- color transform section --------------------------------------
        self._color_mode_combo = QComboBox()
        self._color_mode_combo.addItems(["None", "LUT file (.cube)", "OCIO config"])
        self._color_mode_combo.currentIndexChanged.connect(self._on_color_mode_changed)

        # LUT row
        self._lut_edit = QLineEdit()
        self._lut_edit.setPlaceholderText("Path to .cube file…")
        lut_browse = QPushButton("Browse…")
        lut_browse.clicked.connect(self._browse_lut)
        lut_row = QHBoxLayout()
        lut_row.addWidget(self._lut_edit)
        lut_row.addWidget(lut_browse)
        self._lut_row_widget = QWidget()
        self._lut_row_widget.setLayout(lut_row)
        self._lut_label = QLabel("LUT file:")

        # OCIO rows
        self._ocio_config_edit = QLineEdit()
        self._ocio_config_edit.setPlaceholderText("Path to config.ocio…")
        ocio_browse = QPushButton("Browse…")
        ocio_browse.clicked.connect(self._browse_ocio_config)
        ocio_config_row = QHBoxLayout()
        ocio_config_row.addWidget(self._ocio_config_edit)
        ocio_config_row.addWidget(ocio_browse)
        self._ocio_config_row_widget = QWidget()
        self._ocio_config_row_widget.setLayout(ocio_config_row)
        self._ocio_config_label = QLabel("OCIO config:")

        self._ocio_src_edit = QLineEdit()
        self._ocio_src_edit.setPlaceholderText("e.g. \"Footage - Log\"")
        self._ocio_src_label = QLabel("Source colorspace:")

        self._ocio_dst_edit = QLineEdit()
        self._ocio_dst_edit.setPlaceholderText("e.g. \"ACEScg\"")
        self._ocio_dst_label = QLabel("Dest colorspace:")

        # -- ComfyUI export section -----------------------------------------
        self._comfy_check = QCheckBox("Generate 16-bit PNG sequence (display-referred)")
        self._comfy_check.setChecked(bool(self._defaults.get("comfy", False)))
        self._comfy_check.toggled.connect(self._on_comfy_toggled)

        self._comfy_width_spin = QSpinBox()
        self._comfy_width_spin.setRange(320, 7680)
        self._comfy_width_spin.setSingleStep(64)
        self._comfy_width_spin.setValue(self._defaults.get("comfy_max_width", 1024))

        self._ocio_display_edit = QLineEdit()
        self._ocio_display_edit.setPlaceholderText("e.g. \"sRGB - Display\"")
        self._ocio_view_edit = QLineEdit()
        self._ocio_view_edit.setPlaceholderText("e.g. \"ACES 1.0 - SDR Video\"")

        comfy_hint = QLabel(
            "Display/view are baked using the OCIO config and source "
            "colorspace above. Leave empty to reuse the main color transform."
        )
        comfy_hint.setWordWrap(True)

        comfy_group = QGroupBox("ComfyUI export")
        comfy_form = QFormLayout(comfy_group)
        comfy_form.addRow(self._comfy_check)
        comfy_form.addRow("Max width:", self._comfy_width_spin)
        comfy_form.addRow("OCIO display:", self._ocio_display_edit)
        comfy_form.addRow("OCIO view:", self._ocio_view_edit)
        comfy_form.addRow(comfy_hint)

        # -- burn-in section -----------------------------------------------
        self._burn_frame_check = QCheckBox("Frame number")
        self._burn_source_check = QCheckBox("Source name")
        self._burn_timecode_check = QCheckBox("Timecode")
        burn_group = QGroupBox("Burn-in overlay")
        burn_layout = QVBoxLayout(burn_group)
        burn_layout.addWidget(self._burn_frame_check)
        burn_layout.addWidget(self._burn_source_check)
        burn_layout.addWidget(self._burn_timecode_check)

        # -- form ----------------------------------------------------------
        form = QFormLayout()
        form.addRow("Preset:", self._preset_combo)
        form.addRow("Output directory:", output_row_widget)
        form.addRow("Shot name:", self._shot_edit)
        form.addRow("Shot version:", self._shot_version_spin)
        form.addRow("Proxy max width:", self._proxy_width_spin)
        form.addRow("EXR pixel format:", self._pixfmt_combo)
        form.addRow("EXR compression:", self._exr_codec_combo)
        form.addRow("Frame padding:", self._frame_padding_spin)
        form.addRow("Color transform:", self._color_mode_combo)
        form.addRow(self._lut_label, self._lut_row_widget)
        form.addRow(self._ocio_config_label, self._ocio_config_row_widget)
        form.addRow(self._ocio_src_label, self._ocio_src_edit)
        form.addRow(self._ocio_dst_label, self._ocio_dst_edit)
        form.addRow(comfy_group)
        form.addRow(burn_group)
        form.addRow(self._skip_exr_check)
        form.addRow(self._skip_proxy_check)
        form.addRow(self._nuke_script_check)

        self._mode = mode
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_text = "Add to Queue" if mode == "add_to_queue" else "Export"
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._on_color_mode_changed(0)  # initialise visibility
        self._on_comfy_toggled(self._comfy_check.isChecked())
        self._on_shot_changed(self._shot_edit.text())

    def _on_shot_changed(self, text: str) -> None:
        self._shot_version_spin.setEnabled(bool(text.strip()))

    def _on_preset_changed(self, index: int) -> None:
        if self._suppress_preset:
            return
        if index == 0:
            return
        name = self._preset_names[index - 1]
        values = resolve_preset(name)
        if not values:
            return
        self._proxy_width_spin.setValue(values.get("proxy_max_width", 1920))
        pixfmt = values.get("exr_pixel_format", "gbrpf32le")
        idx = self._pixfmt_combo.findText(pixfmt)
        if idx >= 0:
            self._pixfmt_combo.setCurrentIndex(idx)
        codec = values.get("exr_compression", "zip1")
        idx = self._exr_codec_combo.findText(codec)
        if idx >= 0:
            self._exr_codec_combo.setCurrentIndex(idx)
        self._frame_padding_spin.setValue(values.get("frame_padding", 6))
        self._comfy_check.setChecked(values.get("comfy", False))
        self._comfy_width_spin.setValue(values.get("comfy_max_width", 1024))

    def _on_color_mode_changed(self, index: int) -> None:
        is_lut = index == 1
        is_ocio = index == 2
        # The comfy display/view bake shares the OCIO config + source
        # colorspace fields, so keep them visible while comfy is enabled.
        show_ocio = is_ocio or self._comfy_check.isChecked()
        self._lut_label.setVisible(is_lut)
        self._lut_row_widget.setVisible(is_lut)
        self._ocio_config_label.setVisible(show_ocio)
        self._ocio_config_row_widget.setVisible(show_ocio)
        self._ocio_src_label.setVisible(show_ocio)
        self._ocio_src_edit.setVisible(show_ocio)
        self._ocio_dst_label.setVisible(is_ocio)
        self._ocio_dst_edit.setVisible(is_ocio)
        self.adjustSize()

    def _on_comfy_toggled(self, checked: bool) -> None:
        self._comfy_width_spin.setEnabled(checked)
        self._ocio_display_edit.setEnabled(checked)
        self._ocio_view_edit.setEnabled(checked)
        self._on_color_mode_changed(self._color_mode_combo.currentIndex())

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if directory:
            self._output_dir_edit.setText(directory)

    def _browse_lut(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose LUT file", filter="LUT files (*.cube);;All files (*)"
        )
        if path:
            self._lut_edit.setText(path)

    def _browse_ocio_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose OCIO config", filter="OCIO config (*.ocio);;All files (*)"
        )
        if path:
            self._ocio_config_edit.setText(path)

    def options(self) -> dict:
        """Call after exec() returns Accepted."""
        mode_index = self._color_mode_combo.currentIndex()
        color_mode = ["none", "lut", "ocio"][mode_index]
        burn_in = []
        if self._burn_frame_check.isChecked():
            burn_in.append("frame_number")
        if self._burn_source_check.isChecked():
            burn_in.append("source_name")
        if self._burn_timecode_check.isChecked():
            burn_in.append("timecode")
        return {
            "output_root": self._output_dir_edit.text(),
            "proxy_max_width": self._proxy_width_spin.value(),
            "exr_pixel_format": self._pixfmt_combo.currentText(),
            "exr_compression": self._exr_codec_combo.currentText(),
            "frame_padding": self._frame_padding_spin.value(),
            "skip_exr": self._skip_exr_check.isChecked(),
            "skip_proxy": self._skip_proxy_check.isChecked(),
            "export_nuke_script": self._nuke_script_check.isChecked(),
            "color_mode": color_mode,
            "lut_path": self._lut_edit.text() or None,
            "ocio_config": self._ocio_config_edit.text() or None,
            "ocio_src": self._ocio_src_edit.text() or None,
            "ocio_dst": self._ocio_dst_edit.text() or None,
            "burn_in": burn_in or None,
            "comfy": self._comfy_check.isChecked(),
            "comfy_max_width": self._comfy_width_spin.value(),
            "ocio_display": self._ocio_display_edit.text() or None,
            "ocio_view": self._ocio_view_edit.text() or None,
            "shot": self._shot_edit.text().strip() or None,
            "shot_version": self._shot_version_spin.value() or None,
        }
