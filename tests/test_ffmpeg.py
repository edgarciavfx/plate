from __future__ import annotations

from pathlib import Path

import pytest

from plate.media.ffmpeg import (
    export_exr_sequence,
    export_png_sequence,
    export_proxy,
    _lut_context,
    FFmpegError,
)
from plate.models.frame_range import FrameRange


class TestExportExrSequence:
    def test_builds_correct_ffmpeg_command(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")
        mock_run.return_value = None

        export_exr_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            exr_dir=exr_dir,
            shot_name="test_clip",
            pixel_format="gbrpf32le",
        )

        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-i" in cmd
        assert str(source) in cmd
        assert "-pix_fmt" in cmd
        assert "gbrpf32le" in cmd
        assert "-start_number" in cmd
        assert "1050" in cmd
        assert "-compression" in cmd
        assert "zip1" in cmd
        assert "test_clip.%06d.exr" in cmd[-1]

    def test_custom_compression_and_frame_padding(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_exr_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            exr_dir=exr_dir,
            shot_name="test",
            compression="rle",
            frame_padding=4,
        )

        cmd = mock_run.call_args[0][0]
        comp_idx = cmd.index("-compression")
        assert cmd[comp_idx + 1] == "rle"
        assert "test.%04d.exr" in cmd[-1]

    def test_includes_lut_filter_when_color_transform_active(self, mocker, tmp_path: Path, lut_color_transform):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")
        mocker.patch("plate.color.bake_to_cube", return_value=Path("/tmp/cube.cube"))

        export_exr_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            exr_dir=exr_dir,
            shot_name="test",
            color_transform=lut_color_transform,
        )

        cmd = mock_run.call_args[0][0]
        vf_index = cmd.index("-vf")
        assert "lut3d=" in cmd[vf_index + 1]

    def test_no_lut_filter_when_no_color_transform(self, mocker, tmp_path: Path, empty_color_transform):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_exr_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            exr_dir=exr_dir,
            shot_name="test",
            color_transform=empty_color_transform,
        )

        cmd = mock_run.call_args[0][0]
        assert "-vf" not in cmd

    def test_returns_frame_count(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mocker.patch("plate.media.ffmpeg._run")
        result = export_exr_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            exr_dir=exr_dir,
            shot_name="test",
        )
        assert result == 51

    def test_ffmpeg_not_on_path(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        exr_dir = tmp_path / "exr"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mocker.patch("plate.media.ffmpeg.shutil.which", return_value=None)
        with pytest.raises(FFmpegError, match="not found on PATH"):
            export_exr_sequence(
                source_path=source,
                frame_range=frame_range,
                fps=24.0,
                exr_dir=exr_dir,
                shot_name="test",
            )


class TestExportProxy:
    def test_builds_correct_ffmpeg_command(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        proxy_path = tmp_path / "proxy.mp4"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_proxy(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            proxy_path=proxy_path,
            max_width=1920,
        )

        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-crf" in cmd
        assert "18" in cmd
        assert "-pix_fmt" in cmd
        assert "yuv420p" in cmd
        assert "-movflags" in cmd
        assert "+faststart" in cmd
        assert "-an" in cmd
        assert str(proxy_path) in cmd

    def test_scale_filter_uses_max_width(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        proxy_path = tmp_path / "proxy.mp4"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_proxy(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            proxy_path=proxy_path,
            max_width=1280,
        )

        cmd = mock_run.call_args[0][0]
        vf_index = cmd.index("-vf")
        assert "min(1280,iw)" in cmd[vf_index + 1]

    def test_ffmpeg_not_on_path_proxy(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        proxy_path = tmp_path / "proxy.mp4"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mocker.patch("plate.media.ffmpeg.shutil.which", return_value=None)
        with pytest.raises(FFmpegError, match="not found on PATH"):
            export_proxy(
                source_path=source,
                frame_range=frame_range,
                fps=24.0,
                proxy_path=proxy_path,
            )

    def test_includes_lut_filter_for_proxy(self, mocker, tmp_path: Path, lut_color_transform):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        proxy_path = tmp_path / "proxy.mp4"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")
        mocker.patch("plate.color.bake_to_cube", return_value=Path("/tmp/cube.cube"))

        export_proxy(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            proxy_path=proxy_path,
            color_transform=lut_color_transform,
        )

        cmd = mock_run.call_args[0][0]
        vf_index = cmd.index("-vf")
        vf = cmd[vf_index + 1]
        assert "scale=" in vf
        assert "lut3d=" in vf

    def test_burn_in_frame_number(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        proxy_path = tmp_path / "proxy.mp4"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_proxy(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            proxy_path=proxy_path,
            burn_in=["frame_number", "source_name"],
        )

        cmd = mock_run.call_args[0][0]
        vf_index = cmd.index("-vf")
        vf = cmd[vf_index + 1]
        assert "drawtext" in vf
        assert "Frame %{frame_num}" in vf
        assert "source.mov" in vf


class TestExportPngSequence:
    def test_builds_correct_ffmpeg_command(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        png_dir = tmp_path / "comfy"
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=png_dir,
            shot_name="test_clip",
        )

        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert str(source) in cmd
        pixfmt_idx = cmd.index("-pix_fmt")
        assert cmd[pixfmt_idx + 1] == "rgb48be"
        start_idx = cmd.index("-start_number")
        assert cmd[start_idx + 1] == "1050"
        assert "test_clip.%06d.png" in cmd[-1]

    def test_scale_filter_never_upscales(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=tmp_path / "comfy",
            shot_name="test",
            max_width=1024,
        )

        cmd = mock_run.call_args[0][0]
        vf = cmd[cmd.index("-vf") + 1]
        assert "min(1024,iw)" in vf

    def test_lut_applied_after_scale_and_16bit_format(self, mocker, tmp_path: Path, lut_color_transform):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")
        mocker.patch("plate.color.bake_to_cube", return_value=Path("/tmp/cube.cube"))

        export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=tmp_path / "comfy",
            shot_name="test",
            color_transform=lut_color_transform,
        )

        cmd = mock_run.call_args[0][0]
        vf = cmd[cmd.index("-vf") + 1]
        assert vf.index("scale=") < vf.index("format=rgb48le") < vf.index("lut3d=")

    def test_no_lut_filter_when_no_color_transform(self, mocker, tmp_path: Path, empty_color_transform):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=tmp_path / "comfy",
            shot_name="test",
            color_transform=empty_color_transform,
        )

        cmd = mock_run.call_args[0][0]
        vf = cmd[cmd.index("-vf") + 1]
        assert "lut3d" not in vf
        assert "scale=" in vf

    def test_custom_frame_padding(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mock_run = mocker.patch("plate.media.ffmpeg._run")

        export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=tmp_path / "comfy",
            shot_name="test",
            frame_padding=4,
        )

        cmd = mock_run.call_args[0][0]
        assert "test.%04d.png" in cmd[-1]

    def test_returns_frame_count(self, mocker, tmp_path: Path):
        source = tmp_path / "source.mov"
        source.write_text("fake")
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)

        mocker.patch("plate.media.ffmpeg._run")
        result = export_png_sequence(
            source_path=source,
            frame_range=frame_range,
            fps=24.0,
            png_dir=tmp_path / "comfy",
            shot_name="test",
        )
        assert result == 51

    def test_ffmpeg_not_on_path(self, mocker, tmp_path: Path):
        frame_range = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        mocker.patch("plate.media.ffmpeg.shutil.which", return_value=None)
        with pytest.raises(FFmpegError, match="not found on PATH"):
            export_png_sequence(
                source_path=tmp_path / "source.mov",
                frame_range=frame_range,
                fps=24.0,
                png_dir=tmp_path / "comfy",
                shot_name="test",
            )


class TestLutContext:
    def test_none_color_transform_yields_none(self):
        with _lut_context(None) as cube:
            assert cube is None

    def test_inactive_color_transform_yields_none(self, empty_color_transform):
        with _lut_context(empty_color_transform) as cube:
            assert cube is None

    def test_active_lut_yields_cube_path(self, lut_color_transform, mocker, tmp_path):
        mocker.patch("plate.color.bake_to_cube", return_value=Path("/baked/lut.cube"))
        with _lut_context(lut_color_transform) as cube:
            assert cube == Path("/baked/lut.cube")

    def test_active_ocio_yields_cube_path(self, ocio_color_transform, mocker, tmp_path):
        mocker.patch("plate.color.bake_to_cube", return_value=Path("/baked/lut.cube"))
        with _lut_context(ocio_color_transform) as cube:
            assert cube == Path("/baked/lut.cube")
