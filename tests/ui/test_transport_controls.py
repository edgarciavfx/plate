from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from plate.ui.transport_controls import TransportControls


pytestmark = pytest.mark.gui


class TestTransportControls:
    def test_initial_frame_label(self, qtbot: QtBot):
        tc = TransportControls()
        tc.set_frame_label(1001, 1050, 1100)
        assert "1001" in tc._frame_label.text()
        assert "1050" in tc._frame_label.text()
        assert "1100" in tc._frame_label.text()

    def test_play_pause_button_toggle(self, qtbot: QtBot):
        tc = TransportControls()
        tc.set_playing(True)
        assert tc._play_button.text() == "Pause"
        tc.set_playing(False)
        assert tc._play_button.text() == "Play"

    def test_buttons_emit_signals(self, qtbot: QtBot):
        tc = TransportControls()
        results = []

        tc.playPauseClicked.connect(lambda: results.append("play"))
        tc.stepBackClicked.connect(lambda: results.append("back"))
        tc.stepForwardClicked.connect(lambda: results.append("forward"))
        tc.setInClicked.connect(lambda: results.append("in"))
        tc.setOutClicked.connect(lambda: results.append("out"))

        tc._play_button.click()
        tc._step_back_button.click()
        tc._step_forward_button.click()
        tc._set_in_button.click()
        tc._set_out_button.click()

        assert results == ["play", "back", "forward", "in", "out"]
