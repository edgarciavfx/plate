from __future__ import annotations

import json
from pathlib import Path

import pytest

from plate.media.ffprobe import probe, _parse_frame_rate, FFprobeError


class TestParseFrameRate:
    def test_simple_fraction(self):
        assert _parse_frame_rate("24000/1001") == pytest.approx(23.976, rel=1e-3)

    def test_integer_string(self):
        assert _parse_frame_rate("24") == 24.0

    def test_float_string(self):
        assert _parse_frame_rate("29.97") == pytest.approx(29.97)

    def test_denominator_zero_returns_zero(self):
        assert _parse_frame_rate("10/0") == 0.0

    def test_no_slash(self):
        assert _parse_frame_rate("30") == 30.0


class TestFfprobeProbe:
    def test_source_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            probe("/nonexistent/file.mov")

    def test_successful_probe(self, mocker, tmp_path: Path, sample_ffprobe_json_str: str):
        source = tmp_path / "test.mov"
        source.write_text("fake")

        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = sample_ffprobe_json_str
        mock_run.return_value.returncode = 0

        meta = probe(source)
        assert meta.codec_name == "prores"
        assert meta.width == 4096
        assert meta.height == 2160
        assert meta.fps == pytest.approx(23.976, rel=1e-3)
        assert meta.pixel_format == "yuv422p10le"
        assert meta.bit_depth == 10
        assert meta.colorspace == "bt709"
        assert meta.has_audio is True
        assert meta.audio_codec == "aac"
        assert meta.start_timecode == "01:00:00:00"
        assert meta.total_frames == 240

    def test_no_video_stream_raises(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {"index": 0, "codec_type": "audio", "codec_name": "aac"}
            ],
            "format": {"filename": "test.mov", "duration": "10.0"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)
        mock_run.return_value.returncode = 0

        with pytest.raises(FFprobeError, match="No video stream found"):
            probe(source)

    def test_missing_frame_rate_falls_back(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {
                    "index": 0, "codec_type": "video",
                    "codec_name": "h264", "width": 1920, "height": 1080,
                    "pix_fmt": "yuv420p",
                }
            ],
            "format": {"filename": "test.mov", "duration": "10.0"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)

        meta = probe(source)
        assert meta.fps == 24.0

    def test_missing_duration_falls_back(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {
                    "index": 0, "codec_type": "video",
                    "codec_name": "h264", "width": 1920, "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                }
            ],
            "format": {"filename": "test.mov"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)

        meta = probe(source)
        assert meta.duration_seconds == 0.0

    def test_total_frames_from_nb_frames(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {
                    "index": 0, "codec_type": "video",
                    "codec_name": "h264", "width": 1920, "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                    "nb_frames": "120",
                }
            ],
            "format": {"filename": "test.mov", "duration": "5.0"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)

        meta = probe(source)
        assert meta.total_frames == 120

    def test_total_frames_estimated(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {
                    "index": 0, "codec_type": "video",
                    "codec_name": "h264", "width": 1920, "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                    "duration": "5.0",
                }
            ],
            "format": {"filename": "test.mov"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)

        meta = probe(source)
        assert meta.total_frames == 120

    def test_bit_depth_extraction(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        data = {
            "streams": [
                {
                    "index": 0, "codec_type": "video",
                    "codec_name": "h264", "width": 1920, "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                }
            ],
            "format": {"filename": "test.mov"},
        }
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.return_value.stdout = json.dumps(data)

        meta = probe(source)
        assert meta.bit_depth is None  # "yuv420p" contains no bit-depth token

        data["streams"][0]["pix_fmt"] = "yuv444p12le"
        mock_run.return_value.stdout = json.dumps(data)
        meta = probe(source)
        assert meta.bit_depth == 12

    def test_ffprobe_not_on_path(self, mocker, tmp_path: Path):
        source = tmp_path / "test.mov"
        source.write_text("fake")
        mocker.patch("plate.media.ffprobe.shutil.which", return_value=None)
        with pytest.raises(FFprobeError, match="not found on PATH"):
            probe(source)

    def test_called_process_error_wrapped(self, mocker, tmp_path: Path):
        import subprocess
        source = tmp_path / "test.mov"
        source.write_text("fake")
        mock_run = mocker.patch("plate.media.ffprobe.subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, ["ffprobe"], stderr="error output")

        with pytest.raises(FFprobeError, match="ffprobe failed"):
            probe(source)
