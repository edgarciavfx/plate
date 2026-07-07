from __future__ import annotations

import pytest
from plate.models.frame_range import FrameRange


class TestFrameRange:
    def test_valid_range(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        assert fr.start_frame == 1001
        assert fr.in_frame == 1050
        assert fr.out_frame == 1100

    def test_frame_count(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        assert fr.frame_count == 51

    def test_single_frame(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1050)
        assert fr.frame_count == 1

    def test_in_at_start_frame(self):
        fr = FrameRange(start_frame=1001, in_frame=1001, out_frame=1100)
        assert fr.frame_count == 100
        assert fr.seek_offset_seconds(24) == pytest.approx(0.0)

    def test_seek_offset_seconds(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        result = fr.seek_offset_seconds(24)
        expected = (1050 - 1001) / 24
        assert result == pytest.approx(expected)

    def test_duration_seconds(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        result = fr.duration_seconds(24)
        expected = 51 / 24
        assert result == pytest.approx(expected)

    def test_seek_offset_with_fractional_fps(self):
        fr = FrameRange(start_frame=1001, in_frame=1050, out_frame=1100)
        result = fr.seek_offset_seconds(23.976)
        expected = 49 / 23.976
        assert result == pytest.approx(expected)

    def test_in_frame_before_start_frame_raises(self):
        with pytest.raises(ValueError, match="in_frame"):
            FrameRange(start_frame=1001, in_frame=900, out_frame=1100)

    def test_out_frame_before_in_frame_raises(self):
        with pytest.raises(ValueError, match="out_frame"):
            FrameRange(start_frame=1001, in_frame=1100, out_frame=1050)

    def test_zero_start_frame(self):
        fr = FrameRange(start_frame=0, in_frame=0, out_frame=0)
        assert fr.frame_count == 1
        assert fr.seek_offset_seconds(24) == pytest.approx(0.0)

    def test_is_frozen(self):
        fr = FrameRange(start_frame=0, in_frame=0, out_frame=0)
        with pytest.raises((AttributeError, TypeError)):
            fr.in_frame = 5

    def test_large_frame_range(self):
        fr = FrameRange(start_frame=1, in_frame=1000000, out_frame=2000000)
        assert fr.frame_count == 1000001
