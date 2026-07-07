from __future__ import annotations

from pathlib import Path

import pytest

from plate.export.export_job import ExportJob
from plate.export.proxy_job import ProxyJob
from plate.models.frame_range import FrameRange
from plate.models.plate_session import PlateSession


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
