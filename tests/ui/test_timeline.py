from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from plate.ui.timeline import Timeline


pytestmark = pytest.mark.gui


class TestTimeline:
    def test_initial_state(self, qtbot: QtBot):
        timeline = Timeline()
        assert timeline.in_frame() is None
        assert timeline.out_frame() is None

    def test_set_range(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        assert timeline.in_frame() == 1001
        assert timeline.out_frame() == 1100  # 1001 + 100 - 1

    def test_set_range_single_frame(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=1)
        assert timeline.in_frame() == 1001
        assert timeline.out_frame() == 1001

    def test_current_frame_after_set_range(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        timeline.set_current_frame(1050)
        assert timeline._current_frame == 1050
        timeline.set_current_frame(1060)
        assert timeline._current_frame == 1060

    def test_clamp_in_range(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        assert timeline._clamp(1050) == 1050

    def test_clamp_below_start(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        assert timeline._clamp(0) == 1001

    def test_clamp_above_end(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        assert timeline._clamp(9999) == 1100

    def test_set_in_frame_auto_corrects_out(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        timeline.set_in_frame(1080)
        assert timeline.in_frame() == 1080
        timeline.set_in_frame(1105)  # clamped to 1100, then out pushed to 1100
        assert timeline.in_frame() == 1100
        assert timeline.out_frame() == 1100

    def test_set_out_frame_auto_corrects_in(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        timeline.set_out_frame(1020)
        assert timeline.out_frame() == 1020
        timeline.set_out_frame(1000)  # clamped to 1001, then in pulled to 1001
        assert timeline.out_frame() == 1001
        assert timeline.in_frame() == 1001

    def test_signal_emitted_on_in_changed(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        with qtbot.waitSignal(timeline.inFrameChanged, timeout=1000) as blocker:
            timeline.set_in_frame(1050)
        assert blocker.args[0] == 1050

    def test_signal_emitted_on_out_changed(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=1001, total_frames=100)
        with qtbot.waitSignal(timeline.outFrameChanged, timeout=1000) as blocker:
            timeline.set_out_frame(1080)
        assert blocker.args[0] == 1080

    def test_frame_to_x_simple(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=0, total_frames=100)
        timeline.resize(200, 50)
        x = timeline._frame_to_x(50)
        ratio = 50 / 99
        assert x == int(ratio * 200)

    def test_frame_to_x_single_frame(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=0, total_frames=1)
        timeline.resize(200, 50)
        assert timeline._frame_to_x(0) == 0

    def test_x_to_frame_simple(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=0, total_frames=100)
        timeline.resize(200, 50)
        frame = timeline._x_to_frame(100)
        ratio = 100 / 200
        expected = round(ratio * 99)
        assert frame == expected

    def test_x_to_frame_zero_width(self, qtbot: QtBot):
        timeline = Timeline()
        timeline.set_range(start_frame=0, total_frames=100)
        timeline.resize(0, 50)
        assert timeline._x_to_frame(50) == 0
