from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from plate.ui.viewer import Viewer


pytestmark = [
    pytest.mark.gui,
    pytest.mark.skip(reason="Viewer tests require real multimedia backend (gstreamer)"),
]


class TestViewer:
    def test_create_viewer(self, qtbot: QtBot):
        viewer = Viewer()
        assert viewer is not None

    def test_initial_state(self, qtbot: QtBot):
        viewer = Viewer()
        assert viewer.position_ms() == 0
        assert viewer.is_playing() is False

    def test_toggle_play_pause_safe_no_media(self, qtbot: QtBot):
        viewer = Viewer()
        viewer.toggle_play_pause()
        viewer.toggle_play_pause()
        assert viewer.is_playing() is False

    def test_load_resets_kicked_flag(self, qtbot: QtBot):
        viewer = Viewer()
        viewer._kicked = True
        viewer.load("/nonexistent/file.mov")
        assert viewer._kicked is False
