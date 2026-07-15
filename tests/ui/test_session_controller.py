from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from plate.ui.session_controller import SessionController


pytestmark = pytest.mark.gui


class TestSessionController:
    def test_open_source_success(self, qtbot: QtBot, mocker, tmp_path: Path, sample_metadata):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        mocker.patch("plate.ui.session_controller.probe", return_value=sample_metadata)

        ctrl = SessionController()
        with qtbot.waitSignal(ctrl.metadataLoaded, timeout=2000) as blocker:
            ctrl.open_source(str(source), start_frame=1001)

        assert blocker.signal_triggered
        assert ctrl.metadata is sample_metadata
        assert ctrl.source_path == source
        assert ctrl.start_frame == 1001

    def test_open_source_failure(self, qtbot: QtBot, mocker):
        mocker.patch(
            "plate.ui.session_controller.probe",
            side_effect=FileNotFoundError("not found"),
        )
        ctrl = SessionController()
        with qtbot.waitSignal(ctrl.loadFailed, timeout=2000) as blocker:
            ctrl.open_source("/nonexistent/file.mov")

        assert blocker.signal_triggered
        assert "not found" in blocker.args[0]

    def test_frame_to_ms(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        ctrl.start_frame = 1001
        # frame 1050 -> (1050-1001) / 23.976 * 1000
        expected = round((1050 - 1001) / 23.976 * 1000)
        assert ctrl.frame_to_ms(1050) == expected

    def test_frame_to_ms_no_metadata(self):
        ctrl = SessionController()
        assert ctrl.frame_to_ms(100) == 0

    def test_ms_to_frame(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        ctrl.start_frame = 1001
        # 2000ms -> 1001 + round(2.0 * 23.976)
        result = ctrl.ms_to_frame(2000)
        assert result == 1001 + round(2.0 * 23.976)

    def test_ms_to_frame_no_metadata(self):
        ctrl = SessionController()
        assert ctrl.ms_to_frame(2000) == 0

    def test_total_frames(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        assert ctrl.total_frames() == 240

    def test_total_frames_no_metadata(self):
        ctrl = SessionController()
        assert ctrl.total_frames() == 0

    def test_start_export_no_source(self, qtbot: QtBot):
        ctrl = SessionController()
        with qtbot.waitSignal(ctrl.exportFailed, timeout=2000) as blocker:
            ctrl.start_export(1, 10, {})
        assert blocker.signal_triggered

    def test_color_transform_from_options_none(self):
        ctrl = SessionController()
        ct = ctrl._color_transform_from_options({"color_mode": "none"})
        assert ct is not None
        assert ct.is_active() is False

    def test_color_transform_from_options_lut(self, tmp_path: Path):
        lut = tmp_path / "test.cube"
        lut.write_text("LUT_3D_SIZE 2\n")
        ctrl = SessionController()
        ct = ctrl._color_transform_from_options({
            "color_mode": "lut",
            "lut_path": lut,
        })
        assert ct is not None
        assert ct.is_active() is True
        assert ct.lut_path == lut

    def test_color_transform_from_options_lut_missing_path(self):
        ctrl = SessionController()
        ct = ctrl._color_transform_from_options({
            "color_mode": "lut",
            "lut_path": None,
        })
        assert ct is None

    def test_color_transform_from_options_ocio(self, tmp_path: Path):
        config = tmp_path / "config.ocio"
        config.write_text("ocio_profile_version: 2\n")
        ctrl = SessionController()
        ct = ctrl._color_transform_from_options({
            "color_mode": "ocio",
            "ocio_config": config,
            "ocio_src": "log",
            "ocio_dst": "linear",
        })
        assert ct is not None
        assert ct.is_active() is True
        assert ct.ocio_config == config

    def test_color_transform_from_options_ocio_missing_fields(self):
        ctrl = SessionController()
        ct = ctrl._color_transform_from_options({
            "color_mode": "ocio",
            "ocio_config": "/cfg.ocio",
        })
        assert ct is None

    def test_comfy_transform_from_options_falls_back(self):
        from plate.color import ColorTransform
        ctrl = SessionController()
        fallback = ColorTransform()
        ct = ctrl._comfy_transform_from_options({}, fallback=fallback)
        assert ct is fallback

    def test_comfy_transform_from_options_display_view(self, tmp_path: Path):
        from plate.color import ColorTransform
        config = tmp_path / "config.ocio"
        config.write_text("ocio_profile_version: 2\n")
        ctrl = SessionController()
        ct = ctrl._comfy_transform_from_options({
            "ocio_config": config,
            "ocio_src": "log",
            "ocio_display": "sRGB - Display",
            "ocio_view": "Standard",
        }, fallback=ColorTransform())
        assert ct is not None
        assert ct.is_display_view() is True

    def test_comfy_transform_from_options_invalid(self):
        from plate.color import ColorTransform
        ctrl = SessionController()
        ct = ctrl._comfy_transform_from_options({
            "ocio_display": "sRGB - Display",
            # no view, no config -> invalid
        }, fallback=ColorTransform())
        assert ct is None

    def test_add_to_queue(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        ctrl.start_frame = 1001
        entry = ctrl.add_to_queue("test.mov", 1050, 1100, {})
        assert entry.source == "test.mov"
        assert entry.in_frame == 1050
        assert entry.out_frame == 1100
        assert entry.start_frame == 1001
        assert entry.status == "pending"
        assert entry.comfy is False

    def test_add_to_queue_with_comfy_options(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        entry = ctrl.add_to_queue("test.mov", 1050, 1100, {
            "comfy": True,
            "comfy_max_width": 1280,
            "ocio_display": "sRGB - Display",
            "ocio_view": "Standard",
        })
        assert entry.comfy is True
        assert entry.comfy_max_width == 1280
        assert entry.ocio_display == "sRGB - Display"
        assert entry.ocio_view == "Standard"

    def test_add_to_queue_with_shot_options(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        entry = ctrl.add_to_queue("test.mov", 1050, 1100, {
            "shot": "img01_env",
            "shot_version": 2,
        })
        assert entry.shot == "img01_env"
        assert entry.shot_version == 2

    def test_add_to_queue_shot_defaults_none(self, sample_metadata):
        ctrl = SessionController()
        ctrl.metadata = sample_metadata
        entry = ctrl.add_to_queue("test.mov", 1050, 1100, {})
        assert entry.shot is None
        assert entry.shot_version is None

    def test_start_export_forwards_shot(self, qtbot: QtBot, mocker, tmp_path: Path):
        mock_pipeline = mocker.patch(
            "plate.ui.session_controller.PlatePipeline", autospec=True
        )
        mocker.patch("plate.ui.session_controller._ExportWorker")
        ctrl = SessionController()
        ctrl.source_path = tmp_path / "test.mov"
        ctrl.start_export(1050, 1100, {"shot": "img01_env", "shot_version": 3})
        kwargs = mock_pipeline.call_args[1]
        assert kwargs["shot"] == "img01_env"
        assert kwargs["shot_version"] == 3

    def test_is_queue_running_false_initially(self):
        ctrl = SessionController()
        assert ctrl.is_queue_running() is False
