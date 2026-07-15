from __future__ import annotations

from pathlib import Path

import pytest

from plate.export.comfy_job import ComfyExportJob
from plate.export.export_job import ExportJob
from plate.export.nuke_export import NukeWriter
from plate.export.proxy_job import ProxyJob
from plate.models.frame_range import FrameRange
from plate.models.plate_session import PlateSession


@pytest.fixture
def shot_session(sample_session: PlateSession) -> PlateSession:
    sample_session.shot = "img01_env"
    sample_session.version = 2
    return sample_session


class TestExportJob:
    def test_run_exports_exr_sequence(self, mocker, sample_session: PlateSession):
        sample_session.exr_dir = sample_session.output_dir / "exr"
        sample_session.ensure_output_dirs()

        mock_export = mocker.patch("plate.export.export_job.export_exr_sequence")
        mock_export.return_value = 51

        job = ExportJob(sample_session, pixel_format="gbrpf32le")
        result = job.run()
        assert result == 51
        assert sample_session.exported_frames == 51

    def test_run_raises_without_metadata(self, tmp_path: Path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "out",
            frame_range=FrameRange(1001, 1050, 1100),
            exr_dir=tmp_path / "out" / "exr",
        )
        job = ExportJob(session)
        with pytest.raises(RuntimeError, match="no metadata"):
            job.run()

    def test_run_raises_without_exr_dir(self, sample_session: PlateSession):
        job = ExportJob(sample_session)
        with pytest.raises(RuntimeError, match="not initialized"):
            job.run()

    def test_run_passes_color_transform(self, mocker, sample_session: PlateSession, lut_color_transform):
        sample_session.exr_dir = sample_session.output_dir / "exr"
        sample_session.ensure_output_dirs()

        mock_export = mocker.patch("plate.export.export_job.export_exr_sequence")

        job = ExportJob(sample_session, color_transform=lut_color_transform)
        job.run()
        assert mock_export.call_args[1]["color_transform"] is lut_color_transform

    def test_run_passes_compression_and_frame_padding(self, mocker, sample_session: PlateSession):
        sample_session.exr_dir = sample_session.output_dir / "exr"
        sample_session.ensure_output_dirs()

        mock_export = mocker.patch("plate.export.export_job.export_exr_sequence")

        job = ExportJob(sample_session, compression="piz", frame_padding=4)
        job.run()
        assert mock_export.call_args[1]["compression"] == "piz"
        assert mock_export.call_args[1]["frame_padding"] == 4


class TestProxyJob:
    def test_run_exports_proxy(self, mocker, sample_session: PlateSession):
        mock_proxy = mocker.patch("plate.export.proxy_job.export_proxy")
        mock_proxy.return_value = sample_session.output_dir / "proxy.mp4"

        job = ProxyJob(sample_session, max_width=1920)
        result = job.run()
        assert result == sample_session.output_dir / "proxy.mp4"
        assert sample_session.proxy_path == result

    def test_run_raises_without_metadata(self, tmp_path: Path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "out",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        job = ProxyJob(session)
        with pytest.raises(RuntimeError, match="no metadata"):
            job.run()

    def test_run_passes_max_width(self, mocker, sample_session: PlateSession):
        mock_proxy = mocker.patch("plate.export.proxy_job.export_proxy")

        job = ProxyJob(sample_session, max_width=1280, crf=23)
        job.run()
        assert mock_proxy.call_args[1]["max_width"] == 1280
        assert mock_proxy.call_args[1]["crf"] == 23

    def test_run_passes_color_transform(self, mocker, sample_session: PlateSession, lut_color_transform):
        mock_proxy = mocker.patch("plate.export.proxy_job.export_proxy")

        job = ProxyJob(sample_session, color_transform=lut_color_transform)
        job.run()
        assert mock_proxy.call_args[1]["color_transform"] is lut_color_transform

    def test_run_passes_burn_in(self, mocker, sample_session: PlateSession):
        mock_proxy = mocker.patch("plate.export.proxy_job.export_proxy")

        job = ProxyJob(sample_session, burn_in=["frame_number", "source_name"])
        job.run()
        assert mock_proxy.call_args[1]["burn_in"] == ["frame_number", "source_name"]


class TestComfyExportJob:
    def test_run_exports_png_sequence(self, mocker, sample_session: PlateSession):
        mock_export = mocker.patch("plate.export.comfy_job.export_png_sequence")
        mock_export.return_value = 51

        job = ComfyExportJob(sample_session, max_width=1024)
        result = job.run()

        assert result == 51
        assert mock_export.call_args[1]["png_dir"] == sample_session.output_dir / "comfy"
        assert mock_export.call_args[1]["max_width"] == 1024
        assert sample_session.comfy_dir == sample_session.output_dir / "comfy"
        assert sample_session.comfy_pattern == "test.%06d.png"
        assert sample_session.comfy_frames == 51
        assert sample_session.comfy_max_width == 1024

    def test_run_raises_without_metadata(self, tmp_path: Path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "out",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        job = ComfyExportJob(session)
        with pytest.raises(RuntimeError, match="no metadata"):
            job.run()

    def test_run_passes_color_transform(self, mocker, sample_session: PlateSession, ocio_display_transform):
        mock_export = mocker.patch("plate.export.comfy_job.export_png_sequence")

        job = ComfyExportJob(sample_session, color_transform=ocio_display_transform)
        job.run()
        assert mock_export.call_args[1]["color_transform"] is ocio_display_transform
        assert sample_session.comfy_color_transform is ocio_display_transform

    def test_run_passes_frame_padding(self, mocker, sample_session: PlateSession):
        mock_export = mocker.patch("plate.export.comfy_job.export_png_sequence")

        job = ComfyExportJob(sample_session, frame_padding=4)
        job.run()
        assert mock_export.call_args[1]["frame_padding"] == 4
        assert sample_session.comfy_pattern == "test.%04d.png"


class TestShotModeJobs:
    def test_export_job_uses_versioned_frame_base(self, mocker, shot_session: PlateSession):
        shot_session.ensure_output_dirs()
        mock_export = mocker.patch("plate.export.export_job.export_exr_sequence")

        ExportJob(shot_session).run()
        assert mock_export.call_args[1]["shot_name"] == "img01_env_v002"
        assert mock_export.call_args[1]["exr_dir"] == (
            shot_session.output_dir / "plates" / "img01_env_v002"
        )

    def test_proxy_job_uses_versioned_filename(self, mocker, shot_session: PlateSession):
        mocker.patch("plate.export.proxy_job.export_proxy")

        result = ProxyJob(shot_session).run()
        assert result == shot_session.output_dir / "proxy_v002.mp4"
        assert shot_session.proxy_path == result

    def test_comfy_job_uses_versioned_dir_and_pattern(self, mocker, shot_session: PlateSession):
        mock_export = mocker.patch("plate.export.comfy_job.export_png_sequence")
        mock_export.return_value = 51

        ComfyExportJob(shot_session).run()
        expected_dir = shot_session.output_dir / "comfy" / "img01_env_v002"
        assert mock_export.call_args[1]["png_dir"] == expected_dir
        assert mock_export.call_args[1]["shot_name"] == "img01_env_v002"
        assert shot_session.comfy_dir == expected_dir
        assert shot_session.comfy_pattern == "img01_env_v002.%06d.png"


class TestNukeWriterShotMode:
    def test_read_node_points_at_versioned_plates(self, shot_session: PlateSession):
        shot_session.exr_dir = None  # exercise the plates_dir fallback
        script = NukeWriter(shot_session).build()
        assert "plates/img01_env_v002/img01_env_v002.%06d.exr" in script
        assert "name img01_env_v002_reader" in script

    def test_write_creates_nuke_subfolder(self, shot_session: PlateSession):
        nk_path = NukeWriter(shot_session).write()
        assert nk_path == shot_session.output_dir / "nuke" / "img01_env_v002.nk"
        assert nk_path.exists()

    def test_legacy_write_path_unchanged(self, sample_session: PlateSession):
        sample_session.ensure_output_dirs()
        nk_path = NukeWriter(sample_session).write()
        assert nk_path == sample_session.output_dir / "test.nk"
