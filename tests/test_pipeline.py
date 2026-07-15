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

    def test_comfy_job_runs_when_enabled(self, mocker, tmp_path: Path, ocio_display_transform):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mocker.patch("plate.pipeline.ExportJob", autospec=True)
        mock_comfy_job = mocker.patch("plate.pipeline.ComfyExportJob", autospec=True)

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest.return_value.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
            export_comfy=True,
            comfy_max_width=1280,
            comfy_color_transform=ocio_display_transform,
        )
        pipeline.run(progress=lambda msg, _pct=None: None)

        assert mock_comfy_job.called
        kwargs = mock_comfy_job.call_args[1]
        assert kwargs["max_width"] == 1280
        assert kwargs["color_transform"] is ocio_display_transform
        assert mock_comfy_job.return_value.run.called

    def test_comfy_job_not_run_by_default(self, mocker, tmp_path: Path):
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mocker.patch("plate.pipeline.ExportJob", autospec=True)
        mock_comfy_job = mocker.patch("plate.pipeline.ComfyExportJob", autospec=True)

        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest.return_value.write.return_value = tmp_path / "out" / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path),
            start_frame=1001,
        )
        pipeline.run(progress=lambda msg, _pct=None: None)

        assert not mock_comfy_job.called

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


class TestPipelineShotMode:
    def _run(self, mocker, tmp_path: Path, config=None, **kwargs):
        mocker.patch("plate.pipeline.config.load", return_value=config or {})
        mock_probe = mocker.patch("plate.pipeline.probe")
        mock_metadata = mocker.MagicMock()
        mock_metadata.fps = 24.0
        mock_probe.return_value = mock_metadata

        mocker.patch("plate.pipeline.ProxyJob", autospec=True)
        mocker.patch("plate.pipeline.ExportJob", autospec=True)
        mock_manifest = mocker.patch("plate.pipeline.ManifestWriter", autospec=True)
        mock_manifest.return_value.write.return_value = tmp_path / "manifest.json"

        pipeline = PlatePipeline(
            source=str(tmp_path / "test.mov"),
            in_frame=1050,
            out_frame=1100,
            output_root=str(tmp_path / "shots"),
            **kwargs,
        )
        return pipeline.run(progress=lambda msg, _pct=None: None)

    def test_shot_output_dir_and_scaffold(self, mocker, tmp_path: Path):
        result = self._run(mocker, tmp_path, shot="img01_env")
        session = result.session
        assert session.output_dir == tmp_path / "shots" / "img01_env"
        assert session.shot == "img01_env"
        assert session.version == 1
        for folder in ("ref", "comfy", "paint", "nuke", "renders", "breakdown", "plates"):
            assert (session.output_dir / folder).is_dir()
        assert session.exr_dir == session.output_dir / "plates" / "img01_env_v001"

    def test_auto_version_picks_next_free(self, mocker, tmp_path: Path):
        existing = tmp_path / "shots" / "img01_env" / "plates" / "img01_env_v001"
        existing.mkdir(parents=True)
        result = self._run(mocker, tmp_path, shot="img01_env")
        assert result.session.version == 2
        assert result.session.exr_dir == (
            tmp_path / "shots" / "img01_env" / "plates" / "img01_env_v002"
        )

    def test_forced_version(self, mocker, tmp_path: Path):
        existing = tmp_path / "shots" / "img01_env" / "plates" / "img01_env_v001"
        existing.mkdir(parents=True)
        result = self._run(mocker, tmp_path, shot="img01_env", shot_version=1)
        assert result.session.version == 1

    def test_custom_folders_from_config(self, mocker, tmp_path: Path):
        result = self._run(
            mocker, tmp_path,
            config={"project": {"folders": ["ref", "plates"]}},
            shot="img01_env",
        )
        assert (result.session.output_dir / "ref").is_dir()
        assert not (result.session.output_dir / "paint").exists()

    def test_legacy_mode_unaffected(self, mocker, tmp_path: Path):
        result = self._run(mocker, tmp_path)
        session = result.session
        assert session.shot is None
        assert session.output_dir == tmp_path / "shots" / "test"
        assert session.exr_dir == session.output_dir / "exr"
        assert not (session.output_dir / "ref").exists()
