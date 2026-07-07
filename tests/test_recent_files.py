from __future__ import annotations

import json
from pathlib import Path

from plate.models.recent_files import RecentFiles


class TestRecentFiles:
    def test_load_returns_empty_when_no_file(self, mocker):
        mocker.patch(
            "plate.models.recent_files._RECENT_PATH",
            Path("/nonexistent/recent.json"),
        )
        rf = RecentFiles.load()
        assert rf.paths == []

    def test_record_adds_path_and_trims(self, mocker, tmp_path: Path):
        recent_path = tmp_path / "recent.json"
        mocker.patch("plate.models.recent_files._RECENT_PATH", recent_path)
        mocker.patch("plate.models.recent_files._MAX_ENTRIES", 2)

        rf = RecentFiles.load()
        rf.record("/path/a.mov")
        rf.record("/path/b.mov")
        rf.record("/path/c.mov")
        assert rf.paths == ["/path/c.mov", "/path/b.mov"]

    def test_record_deduplicates(self, mocker, tmp_path: Path):
        recent_path = tmp_path / "recent.json"
        mocker.patch("plate.models.recent_files._RECENT_PATH", recent_path)

        rf = RecentFiles.load()
        rf.record("/path/a.mov")
        rf.record("/path/b.mov")
        rf.record("/path/a.mov")
        assert rf.paths == ["/path/a.mov", "/path/b.mov"]

    def test_save_and_reload(self, mocker, tmp_path: Path):
        recent_path = tmp_path / "recent.json"
        mocker.patch("plate.models.recent_files._RECENT_PATH", recent_path)

        rf = RecentFiles.load()
        rf.record("/path/a.mov")
        rf.record("/path/b.mov")

        rf2 = RecentFiles.load()
        assert rf2.paths == ["/path/b.mov", "/path/a.mov"]

    def test_load_handles_corrupted_json(self, mocker, tmp_path: Path):
        recent_path = tmp_path / "recent.json"
        recent_path.write_text("not json")
        mocker.patch("plate.models.recent_files._RECENT_PATH", recent_path)

        rf = RecentFiles.load()
        assert rf.paths == []

    def test_load_handles_non_list_json(self, mocker, tmp_path: Path):
        recent_path = tmp_path / "recent.json"
        recent_path.write_text(json.dumps({"path": "/test.mov"}))
        mocker.patch("plate.models.recent_files._RECENT_PATH", recent_path)

        rf = RecentFiles.load()
        assert rf.paths == []

    def test_paths_property(self):
        rf = RecentFiles(entries=[
            {"path": "/a.mov", "timestamp": "2024-01-01"},
            {"path": "/b.mov", "timestamp": "2024-01-02"},
        ])
        assert rf.paths == ["/a.mov", "/b.mov"]
