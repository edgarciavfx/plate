from __future__ import annotations

import pytest

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
        bit_depth=8,
        has_audio=True,
        total_frames=240,
        raw={},
    )
