from __future__ import annotations

from pathlib import Path

from plate.cli import build_parser, main


class TestVersion:
    def test_version_flag(self):
        from plate import __version__ as expected
        parser = build_parser()
        try:
            parser.parse_args(["--version"])
        except SystemExit as exc:
            assert exc.code == 0


class TestBuildParser:
    def test_parser_has_source_arg(self):
        parser = build_parser()
        ns = parser.parse_args(["test.mov", "--in", "10", "--out", "20"])
        assert ns.source == "test.mov"
        assert ns.in_frame == 10
        assert ns.out_frame == 20

    def test_parser_defaults(self):
        parser = build_parser()
        ns = parser.parse_args(["test.mov", "--in", "10", "--out", "20"])
        assert ns.start_frame is None
        assert ns.output_root == "./output"
        assert ns.proxy_max_width == 1920
        assert ns.exr_pixel_format == "gbrpf32le"
        assert ns.exr_compression == "zip1"
        assert ns.frame_padding == 6
        assert ns.skip_exr is False
        assert ns.skip_proxy is False
        assert ns.lut_path is None
        assert ns.ocio_config is None
        assert ns.burn_in is None

    def test_parser_batch_mode(self):
        parser = build_parser()
        ns = parser.parse_args(["--batch", "jobs.json"])
        assert ns.batch == "jobs.json"
        assert ns.source is None

    def test_parser_flags(self):
        parser = build_parser()
        ns = parser.parse_args([
            "test.mov", "--in", "1001", "--out", "1100",
            "--start-frame", "1001", "--output", "./out",
            "--proxy-width", "1280",             "--exr-codec", "zip16",
            "--frame-padding", "4", "--burn-in", "frame_number",
            "--burn-in", "source_name", "--skip-exr",
        ])
        assert ns.start_frame == 1001
        assert ns.output_root == "./out"
        assert ns.proxy_max_width == 1280
        assert ns.exr_compression == "zip16"
        assert ns.frame_padding == 4
        assert ns.burn_in == ["frame_number", "source_name"]
        assert ns.skip_exr is True
        assert ns.skip_proxy is False


class TestMain:
    def test_no_source_no_batch_returns_1(self):
        rc = main(["--in", "10", "--out", "20"])
        assert rc == 1

    def test_source_and_batch_together_returns_1(self):
        rc = main(["test.mov", "--batch", "jobs.json"])
        assert rc == 1

    def test_missing_in_out_in_single_mode_returns_1(self):
        rc = main(["test.mov"])
        assert rc == 1

    def test_missing_out_in_single_mode_returns_1(self):
        rc = main(["test.mov", "--in", "10"])
        assert rc == 1

    def test_single_mode_success(self, mocker):
        mocker.patch("plate.cli.PlatePipeline", autospec=True)
        mock_instance = mocker.patch("plate.cli.PlatePipeline").return_value
        mock_instance.run.return_value = mocker.MagicMock()

        rc = main(["test.mov", "--in", "10", "--out", "20"])
        assert rc == 0

    def test_single_mode_file_not_found(self, mocker):
        mock_pipeline = mocker.patch("plate.cli.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        mock_instance.run.side_effect = FileNotFoundError("file not found")

        rc = main(["test.mov", "--in", "10", "--out", "20"])
        assert rc == 1

    def test_single_mode_ffmpeg_error(self, mocker):
        mock_pipeline = mocker.patch("plate.cli.PlatePipeline", autospec=True)
        mock_instance = mock_pipeline.return_value
        from plate.media.ffmpeg import FFmpegError
        mock_instance.run.side_effect = FFmpegError("ffmpeg failed")

        rc = main(["test.mov", "--in", "10", "--out", "20"])
        assert rc == 1

    def test_batch_mode_success(self, mocker, tmp_path: Path):
        batch_file = tmp_path / "batch.json"
        batch_file.write_text('[]')
        mocker.patch("plate.cli.load_batch_file", return_value=[])
        rc = main(["--batch", str(batch_file)])
        assert rc == 1  # empty batch returns 1

    def test_lut_and_ocio_mutually_exclusive(self, mocker):
        rc = main([
            "test.mov", "--in", "10", "--out", "20",
            "--lut", "test.cube", "--ocio-config", "config.ocio",
        ])
        assert rc == 1

    def test_ocio_missing_src_dst(self, mocker):
        rc = main([
            "test.mov", "--in", "10", "--out", "20",
            "--ocio-config", "config.ocio",
        ])
        assert rc == 1

    def test_batch_mode_load_error(self, mocker):
        mocker.patch("plate.cli.load_batch_file", side_effect=FileNotFoundError("no file"))
        rc = main(["--batch", "nonexistent.json"])
        assert rc == 1
