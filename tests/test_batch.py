from __future__ import annotations

import json
from pathlib import Path

import pytest

from plate.batch import BatchEntry, load_batch_file, _resolve_color, run_batch
from plate.color import ColorTransform


class TestLoadBatchFile:
    def test_valid_batch_file(self, tmp_path: Path):
        data = [
            {"source": "a.mov", "in": 1001, "out": 1100},
            {"source": "b.mov", "in": 1204, "out": 1389, "start_frame": 1001},
        ]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        entries = load_batch_file(path)
        assert len(entries) == 2
        assert entries[0].source == "a.mov"
        assert entries[0].in_frame == 1001
        assert entries[0].out_frame == 1100
        assert entries[0].start_frame is None
        assert entries[1].start_frame == 1001

    def test_missing_source_field_raises(self, tmp_path: Path):
        data = [{"in": 1001, "out": 1100}]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing required 'source'"):
            load_batch_file(path)

    def test_missing_in_field_raises(self, tmp_path: Path):
        data = [{"source": "a.mov", "out": 1100}]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing required 'in'"):
            load_batch_file(path)

    def test_missing_out_field_raises(self, tmp_path: Path):
        data = [{"source": "a.mov", "in": 1001}]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing required 'out'"):
            load_batch_file(path)

    def test_non_array_root_raises(self, tmp_path: Path):
        data = {"source": "a.mov"}
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="JSON array"):
            load_batch_file(path)

    def test_non_dict_entry_raises(self, tmp_path: Path):
        data = ["not_a_dict"]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="not a JSON object"):
            load_batch_file(path)

    def test_empty_array_returns_empty_list(self, tmp_path: Path):
        path = tmp_path / "batch.json"
        path.write_text(json.dumps([]))
        entries = load_batch_file(path)
        assert entries == []

    def test_optional_fields_are_translated(self, tmp_path: Path):
        data = [{
            "source": "a.mov", "in": 1001, "out": 1100,
            "start_frame": 1001, "output": "./shots",
            "proxy_width": 1280, "exr_pixfmt": "gbrpf32le",
            "exr_codec": "zip16", "frame_padding": 4,
            "skip_exr": False, "skip_proxy": True,
            "lut": "/path/to/lut.cube",
            "burn_in": ["frame_number"],
        }]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        entries = load_batch_file(path)
        e = entries[0]
        assert e.start_frame == 1001
        assert e.output_root == "./shots"
        assert e.proxy_max_width == 1280
        assert e.exr_pixel_format == "gbrpf32le"
        assert e.exr_compression == "zip16"
        assert e.frame_padding == 4
        assert e.skip_exr is False
        assert e.skip_proxy is True
        assert e.lut_path == "/path/to/lut.cube"
        assert e.burn_in == ["frame_number"]

    def test_missing_json_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_batch_file("/nonexistent/batch.json")

    def test_shot_fields_parsed(self, tmp_path: Path):
        data = [{
            "source": "a.mov", "in": 1001, "out": 1100,
            "shot": "img01_env", "shot_version": 2,
        }]
        path = tmp_path / "batch.json"
        path.write_text(json.dumps(data))
        entry = load_batch_file(path)[0]
        assert entry.shot == "img01_env"
        assert entry.shot_version == 2

    def test_shot_fields_default_none(self, tmp_path: Path):
        path = tmp_path / "batch.json"
        path.write_text(json.dumps([{"source": "a.mov", "in": 1, "out": 10}]))
        entry = load_batch_file(path)[0]
        assert entry.shot is None
        assert entry.shot_version is None


class TestResolveColor:
    def test_no_color(self, sample_batch_entry: BatchEntry):
        ct = _resolve_color(sample_batch_entry)
        assert isinstance(ct, ColorTransform)
        assert ct.is_active() is False

    def test_lut_color(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.lut_path = "/path/to/lut.cube"
        ct = _resolve_color(sample_batch_entry)
        assert ct.is_active() is True
        assert ct.lut_path == Path("/path/to/lut.cube")

    def test_ocio_color(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        sample_batch_entry.ocio_src = "log"
        sample_batch_entry.ocio_dst = "linear"
        ct = _resolve_color(sample_batch_entry)
        assert ct.is_active() is True
        assert ct.ocio_config == Path("/path/to/config.ocio")

    def test_lut_and_ocio_mutually_exclusive(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.lut_path = "/path/to/lut.cube"
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        with pytest.raises(ValueError, match="mutually exclusive"):
            _resolve_color(sample_batch_entry)

    def test_ocio_src_without_config_raises(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.ocio_src = "log"
        with pytest.raises(ValueError, match="require ocio_config"):
            _resolve_color(sample_batch_entry)

    def test_ocio_config_missing_src_dst_raises(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        with pytest.raises(ValueError, match="requires ocio_src"):
            _resolve_color(sample_batch_entry)

    def test_display_only_leaves_main_transform_inactive(self, sample_batch_entry: BatchEntry):
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        sample_batch_entry.ocio_src = "log"
        ct = _resolve_color(
            sample_batch_entry, ocio_display="sRGB - Display", ocio_view="Standard"
        )
        assert ct.is_active() is False


class TestResolveComfyColor:
    def test_display_view_builds_display_transform(self, sample_batch_entry: BatchEntry):
        from plate.batch import _resolve_comfy_color
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        sample_batch_entry.ocio_src = "log"
        sample_batch_entry.ocio_display = "sRGB - Display"
        sample_batch_entry.ocio_view = "Standard"
        ct = _resolve_comfy_color(sample_batch_entry, fallback=ColorTransform())
        assert ct.is_display_view() is True
        assert ct.display == "sRGB - Display"

    def test_defaults_used_when_entry_has_no_display(self, sample_batch_entry: BatchEntry):
        from plate.batch import _resolve_comfy_color
        sample_batch_entry.ocio_config = "/path/to/config.ocio"
        sample_batch_entry.ocio_src = "log"
        ct = _resolve_comfy_color(
            sample_batch_entry,
            fallback=ColorTransform(),
            default_display="sRGB - Display",
            default_view="Standard",
        )
        assert ct.is_display_view() is True

    def test_falls_back_without_display(self, sample_batch_entry: BatchEntry):
        from plate.batch import _resolve_comfy_color
        fallback = ColorTransform(lut_path=Path("/some/lut.cube"))
        ct = _resolve_comfy_color(sample_batch_entry, fallback=fallback)
        assert ct is fallback


class TestRunBatch:
    def test_run_batch_calls_progress(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        mock_instance.run.return_value = mocker.MagicMock()

        progress = mocker.MagicMock()
        results = run_batch(
            [sample_batch_entry],
            defaults={"output_root": "./out"},
            progress=progress,
        )
        assert len(results) == 1
        assert results[0].error is None
        progress.assert_any_call("[1/1] Processing test.mov...")

    def test_run_batch_collects_errors(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        mock_instance.run.side_effect = RuntimeError("something went wrong")

        results = run_batch(
            [sample_batch_entry],
            defaults={"output_root": "./out"},
        )
        assert len(results) == 1
        assert results[0].error is not None
        assert "something went wrong" in str(results[0].error)

    def test_run_batch_continues_on_failure(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        mock_instance.run.side_effect = [RuntimeError("fail"), mocker.MagicMock()]

        entry_a = BatchEntry(source="a.mov", in_frame=1, out_frame=10)
        entry_b = BatchEntry(source="b.mov", in_frame=1, out_frame=10)

        results = run_batch(
            [entry_a, entry_b],
            defaults={"output_root": "./out"},
        )
        assert len(results) == 2
        assert results[0].error is not None
        assert results[1].error is None

    def test_run_batch_falls_back_to_defaults(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        mock_instance.run.return_value = mocker.MagicMock()

        entry = BatchEntry(source="test.mov", in_frame=1050, out_frame=1100)
        run_batch(
            [entry],
            defaults={
                "output_root": "./default_out",
                "start_frame": 1001,
                "proxy_max_width": 1920,
                "exr_pixel_format": "gbrpf32le",
                "exr_compression": "zip1",
                "frame_padding": 6,
                "skip_exr": False,
                "skip_proxy": False,
            },
        )
        _, kwargs = mock_pipeline.call_args
        assert kwargs["output_root"] == "./default_out"
        assert kwargs["start_frame"] == 1001
        assert kwargs["exr_compression"] == "zip1"
        assert kwargs["frame_padding"] == 6

    def test_run_batch_comfy_disabled_by_default(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_pipeline.return_value.run.return_value = mocker.MagicMock()

        run_batch([sample_batch_entry], defaults={"output_root": "./out"})
        _, kwargs = mock_pipeline.call_args
        assert kwargs["export_comfy"] is False
        assert kwargs["comfy_color_transform"] is None

    def test_run_batch_comfy_with_display_defaults(self, mocker):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_pipeline.return_value.run.return_value = mocker.MagicMock()

        entry = BatchEntry(
            source="test.mov", in_frame=1, out_frame=10,
            ocio_config="/cfg.ocio", ocio_src="log", comfy=True,
        )
        run_batch(
            [entry],
            defaults={
                "output_root": "./out",
                "comfy_max_width": 1280,
                "ocio_display": "sRGB - Display",
                "ocio_view": "Standard",
            },
        )
        _, kwargs = mock_pipeline.call_args
        assert kwargs["export_comfy"] is True
        assert kwargs["comfy_max_width"] == 1280
        assert kwargs["comfy_color_transform"].is_display_view() is True
        # display/view without ocio_dst leaves the main transform inactive
        assert kwargs["color_transform"].is_active() is False

    def test_run_batch_forwards_shot_fields(self, mocker):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_pipeline.return_value.run.return_value = mocker.MagicMock()

        entry = BatchEntry(
            source="test.mov", in_frame=1, out_frame=10,
            shot="img01_env", shot_version=3,
        )
        run_batch([entry], defaults={"output_root": "./out"})
        _, kwargs = mock_pipeline.call_args
        assert kwargs["shot"] == "img01_env"
        assert kwargs["shot_version"] == 3

    def test_run_batch_shot_defaults_none(self, mocker, sample_batch_entry: BatchEntry):
        mock_pipeline = mocker.patch("plate.batch.PlatePipeline", autospec=True)
        mock_pipeline.return_value.run.return_value = mocker.MagicMock()

        run_batch([sample_batch_entry], defaults={"output_root": "./out"})
        _, kwargs = mock_pipeline.call_args
        assert kwargs["shot"] is None
        assert kwargs["shot_version"] is None
