from __future__ import annotations

from pathlib import Path

import pytest

from plate.presets import ExportPreset, load_user_presets, resolve_preset


class TestExportPreset:
    def test_to_dict_includes_comfy_keys(self):
        preset = ExportPreset(name="Test", comfy=True, comfy_max_width=1280)
        d = preset.to_dict()
        assert d["comfy"] is True
        assert d["comfy_max_width"] == 1280

    def test_comfy_defaults_off(self):
        preset = ExportPreset(name="Test")
        assert preset.comfy is False
        assert preset.comfy_max_width == 1024


class TestUserPresets:
    def test_old_preset_file_without_comfy_keys_loads(self, mocker, tmp_path: Path):
        preset_file = tmp_path / "presets.toml"
        preset_file.write_text(
            '["My Old Preset"]\nproxy_max_width = 1280\nexr_compression = "rle"\n'
        )
        mocker.patch("plate.presets._PRESET_PATH", preset_file)
        presets = load_user_presets()
        assert presets["My Old Preset"].comfy is False

    def test_preset_with_comfy_keys(self, mocker, tmp_path: Path):
        preset_file = tmp_path / "presets.toml"
        preset_file.write_text(
            '["Comfy 1280"]\ncomfy = true\ncomfy_max_width = 1280\n'
        )
        mocker.patch("plate.presets._PRESET_PATH", preset_file)
        values = resolve_preset("Comfy 1280")
        assert values["comfy"] is True
        assert values["comfy_max_width"] == 1280
