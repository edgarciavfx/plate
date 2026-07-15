from __future__ import annotations

from pathlib import Path

import pytest

from plate.project import (
    DEFAULT_SHOT_FOLDERS,
    next_version,
    resolve_folders,
    scaffold_shot,
    versioned_name,
)


class TestVersionedName:
    def test_three_digit_padding(self):
        assert versioned_name("img01_env", 1) == "img01_env_v001"
        assert versioned_name("img01_env", 10) == "img01_env_v010"
        assert versioned_name("img01_env", 100) == "img01_env_v100"

    def test_four_digits_kept(self):
        assert versioned_name("shot", 1000) == "shot_v1000"


class TestScaffoldShot:
    def test_creates_default_folders(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        assert shot_dir == tmp_path / "img01_env"
        for folder in DEFAULT_SHOT_FOLDERS:
            assert (shot_dir / folder).is_dir()

    def test_custom_folder_list(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env", ["ref", "plates"])
        assert (shot_dir / "ref").is_dir()
        assert (shot_dir / "plates").is_dir()
        assert not (shot_dir / "paint").exists()

    def test_idempotent(self, tmp_path: Path):
        scaffold_shot(tmp_path, "img01_env")
        (tmp_path / "img01_env" / "ref" / "board.jpg").write_text("x")
        scaffold_shot(tmp_path, "img01_env")
        assert (tmp_path / "img01_env" / "ref" / "board.jpg").exists()

    def test_rejects_path_separators(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Invalid shot name"):
            scaffold_shot(tmp_path, "a/b")

    def test_rejects_empty_and_dot_leading(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Invalid shot name"):
            scaffold_shot(tmp_path, "")
        with pytest.raises(ValueError, match="Invalid shot name"):
            scaffold_shot(tmp_path, ".hidden")


class TestNextVersion:
    def test_missing_shot_dir_returns_1(self, tmp_path: Path):
        assert next_version(tmp_path / "nope", "img01_env") == 1

    def test_empty_scaffold_returns_1(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        assert next_version(shot_dir, "img01_env") == 1

    def test_plates_dirs_counted(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        (shot_dir / "plates" / "img01_env_v001").mkdir()
        (shot_dir / "plates" / "img01_env_v003").mkdir()
        assert next_version(shot_dir, "img01_env") == 4

    def test_proxy_files_counted(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        (shot_dir / "proxy_v002.mp4").write_text("x")
        assert next_version(shot_dir, "img01_env") == 3

    def test_nuke_scripts_counted(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        (shot_dir / "nuke" / "img01_env_v005.nk").write_text("x")
        assert next_version(shot_dir, "img01_env") == 6

    def test_other_shots_ignored(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        (shot_dir / "plates" / "otherShot_v009").mkdir()
        assert next_version(shot_dir, "img01_env") == 1

    def test_comfy_dirs_counted(self, tmp_path: Path):
        shot_dir = scaffold_shot(tmp_path, "img01_env")
        (shot_dir / "comfy" / "img01_env_v002").mkdir()
        assert next_version(shot_dir, "img01_env") == 3


class TestResolveFolders:
    def test_none_config_returns_default(self):
        assert resolve_folders(None) == DEFAULT_SHOT_FOLDERS

    def test_config_without_project_returns_default(self):
        assert resolve_folders({"export": {}}) == DEFAULT_SHOT_FOLDERS

    def test_config_folders_used(self):
        cfg = {"project": {"folders": ["ref", "plates"]}}
        assert resolve_folders(cfg) == ["ref", "plates"]

    def test_invalid_folders_falls_back(self):
        assert resolve_folders({"project": {"folders": "ref"}}) == DEFAULT_SHOT_FOLDERS
        assert resolve_folders({"project": {"folders": [1, 2]}}) == DEFAULT_SHOT_FOLDERS
