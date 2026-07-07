from __future__ import annotations

from pathlib import Path

from plate.pipeline import PlatePipeline


class TestPlatePipeline:
    def test_run_full_pipeline(self, mocker, tmp_path: Path, sample_ffprobe_json_str: str):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mock_proxy_job = mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mock_proxy_instance = mock_proxy_job.return_value

        mock_export_job = mocker.patch("plate.pipeline.ExportJob", autospec=True)
        mock_export_instance = mock_export_job.return_value

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
        )
        result = pipeline.run(progress=lambda msg, _pct=None: None)

        assert mock_probe.called
        assert mock_proxy_job.called
        assert mock_export_job.called
        assert mock_manifest_instance.write.called
        assert result.manifest_path is not None

    def test_skip_proxy(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mock_export_job = mocker.patch("plate.pipeline.ExportJob", autospec=True)
        mock_export_instance = mock_export_job.return_value

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
            skip_proxy=True,
        )
        pipeline.run(progress=lambda msg, _pct=None: None)

        assert not mocker.patch("plate.pipeline.ProxyJob").called

    def test_skip_exr(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mock_proxy_job = mocker.patch("plate.pipeline.ProxyJob", autospec=True)

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
            skip_exr=True,
        )
        pipeline.run(progress=lambda msg, _pct=None: None)

        assert not mocker.patch("plate.pipeline.ExportJob").called

    def test_skip_both(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
            skip_exr=True,
            skip_proxy=True,
        )
        result = pipeline.run(progress=lambda msg, _pct=None: None)
        assert result.manifest_path is not None

    def test_progress_callback_called(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mocker.patch("plate.pipeline.ExportJob", autospec=True)

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "manifest.json"

        messages = []
        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
        )
        pipeline.run(progress=lambda msg, _pct=None: messages.append(msg))

        assert any("Inspecting" in m for m in messages)
        assert any("Generating proxy" in m for m in messages)
        assert any("Generating EXR" in m for m in messages)
        assert any("Writing manifest" in m for m in messages)
        assert any("Done" in m for m in messages)

    def test_creates_shot_subdirectory(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mocker.patch("plate.pipeline.ExportJob", autospec=True)

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest_instance = mock_manifest.return_value
        mock_manifest_instance.write.return_value = tmp_path / "out" / "test" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
        )
        result = pipeline.run(progress=lambda msg, _pct=None: None)
        assert result.session.output_dir == tmp_path / "test"
