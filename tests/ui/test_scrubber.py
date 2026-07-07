from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from plate.ui.scrubber import Scrubber


pytestmark = pytest.mark.gui


class TestScrubber:
    def test_initial_range_zero(self, qtbot: QtBot):
        scrub = Scrubber()
        assert scrub.minimum() == 0
        assert scrub.maximum() == 0

    def test_set_position_updates_value(self, qtbot: QtBot):
        scrub = Scrubber()
        scrub.set_duration(10000)
        scrub.set_position(5000)
        assert scrub.value() == 5000

    def test_set_programmatic_position_does_not_emit_seek(self, qtbot: QtBot):
        scrub = Scrubber()
        scrub.set_duration(10000)
        scrub.set_position(3000)
        signals = []
        scrub.seekRequested.connect(signals.append)
        scrub.set_position(5000)
        assert len(signals) == 0

    def test_user_drag_emits_seek(self, qtbot: QtBot):
        scrub = Scrubber()
        scrub.set_duration(10000)
        signals = []
        scrub.seekRequested.connect(signals.append)
        scrub._on_user_seek(4000)
        assert len(signals) == 1
        assert signals[0] == 4000

    def test_user_press_emits_seek(self, qtbot: QtBot):
        scrub = Scrubber()
        scrub.set_duration(10000)
        scrub.setValue(2500)
        signals = []
        scrub.seekRequested.connect(signals.append)
        scrub._on_user_press()
        assert len(signals) == 1
        assert signals[0] == 2500
