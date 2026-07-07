from __future__ import annotations

from plate.models.video_metadata import VideoMetadata


class TestVideoMetadata:
    def test_to_dict_excludes_raw(self):
        meta = VideoMetadata(
            path="test.mov",
            duration_seconds=10.0,
            fps=23.976,
            width=1920,
            height=1080,
            codec_name="h264",
            raw={"some": "data"},
        )
        d = meta.to_dict()
        assert "raw" not in d
        assert d["duration_seconds"] == 10.0
        assert d["width"] == 1920
        assert d["codec_name"] == "h264"

    def test_to_dict_rounds_fps_to_3_decimals(self):
        meta = VideoMetadata(
            path="test.mov",
            duration_seconds=10.0,
            fps=23.976023976023978,
            width=1920,
            height=1080,
            codec_name="h264",
        )
        d = meta.to_dict()
        assert d["fps"] == 23.976

    def test_to_dict_optional_fields_default_to_none(self):
        meta = VideoMetadata(
            path="test.mov",
            duration_seconds=10.0,
            fps=24.0,
            width=1920,
            height=1080,
            codec_name="h264",
        )
        d = meta.to_dict()
        assert d["pixel_format"] is None
        assert d["colorspace"] is None
        assert d["bit_depth"] is None
        assert d["has_audio"] is False
        assert d["audio_codec"] is None
        assert d["start_timecode"] is None
        assert d["total_frames"] is None

    def test_to_dict_includes_all_fields(self):
        meta = VideoMetadata(
            path="test.mov",
            duration_seconds=10.0,
            fps=24.0,
            width=4096,
            height=2160,
            codec_name="prores",
            pixel_format="yuv422p10le",
            colorspace="bt709",
            color_transfer="bt709",
            color_primaries="bt709",
            bit_depth=10,
            has_audio=True,
            audio_codec="aac",
            start_timecode="01:00:00:00",
            total_frames=240,
        )
        d = meta.to_dict()
        assert d["pixel_format"] == "yuv422p10le"
        assert d["colorspace"] == "bt709"
        assert d["bit_depth"] == 10
        assert d["has_audio"] is True
        assert d["audio_codec"] == "aac"
        assert d["start_timecode"] == "01:00:00:00"
        assert d["total_frames"] == 240
        assert d["fps"] == 24.0

    def test_repr_excludes_raw(self):
        meta = VideoMetadata(
            path="test.mov",
            duration_seconds=1.0,
            fps=24.0,
            width=100,
            height=100,
            codec_name="test",
            raw={"secret": "data"},
        )
        r = repr(meta)
        assert "secret" not in r
        assert "raw" not in r
