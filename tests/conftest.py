from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from plate.batch import BatchEntry
from plate.color import ColorTransform
from plate.models.frame_range import FrameRange
from plate.models.plate_session import PlateSession
from plate.models.shot_queue import QueueEntry
from plate.models.video_metadata import VideoMetadata


@pytest.fixture
def sample_metadata() -> VideoMetadata:
    return VideoMetadata(
        path="test.mov",
        duration_seconds=10.0,
        fps=23.976,
        width=1920,
        height=1080,
        codec_name="h264",
        pixel_format="yuv420p",
        colorspace="bt709",
        color_transfer="bt709",
        color_primaries="bt709",
        bit_depth=8,
        has_audio=True,
        audio_codec="aac",
        start_timecode="01:00:00:00",
        total_frames=240,
        raw={},
    )


@pytest.fixture
def sample_frame_range() -> FrameRange:
    return FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)


@pytest.fixture
def sample_session(sample_metadata: VideoMetadata, sample_frame_range: FrameRange, tmp_path: Path) -> PlateSession:
    return PlateSession(
        source_path=Path("test.mov"),
        output_dir=tmp_path / "output",
        frame_range=sample_frame_range,
        metadata=sample_metadata,
    )


@pytest.fixture
def sample_batch_entry() -> BatchEntry:
    return BatchEntry(
        source="test.mov",
        in_frame=1050,
        out_frame=1100,
        start_frame=1001,
    )


@pytest.fixture
def sample_ffprobe_json() -> dict[str, Any]:
    return {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "prores",
                "width": 4096,
                "height": 2160,
                "pix_fmt": "yuv422p10le",
                "r_frame_rate": "24000/1001",
                "duration": "10.01",
                "nb_frames": "240",
                "bits_per_raw_sample": "10",
                "color_space": "bt709",
                "color_transfer": "bt709",
                "color_primaries": "bt709",
                "tags": {"timecode": "01:00:00:00"},
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
            },
        ],
        "format": {
            "filename": "test.mov",
            "duration": "10.01",
        },
    }


@pytest.fixture
def sample_ffprobe_json_str(sample_ffprobe_json: dict[str, Any]) -> str:
    return json.dumps(sample_ffprobe_json)


@pytest.fixture
def sample_queue_entry() -> QueueEntry:
    return QueueEntry(
        source="test.mov",
        in_frame=1050,
        out_frame=1100,
        start_frame=1001,
        status="pending",
    )


@pytest.fixture
def empty_color_transform() -> ColorTransform:
    return ColorTransform()


@pytest.fixture
def lut_color_transform() -> ColorTransform:
    return ColorTransform(lut_path=Path("/some/lut.cube"))


@pytest.fixture
def ocio_color_transform() -> ColorTransform:
    return ColorTransform(
        ocio_config=Path("/some/config.ocio"),
        src_colorspace="log",
        dst_colorspace="linear",
    )


@pytest.fixture
def ocio_display_transform() -> ColorTransform:
    return ColorTransform(
        ocio_config=Path("/some/config.ocio"),
        src_colorspace="log",
        display="sRGB - Display",
        view="ACES 1.0 - SDR Video",
    )
