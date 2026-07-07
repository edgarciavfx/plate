from __future__ import annotations

from pathlib import Path

from plate.config import EXPORT_DEFAULTS, load, merge


class TestLoadConfig:
    def test_load_returns_empty_when_no_config(self, mocker):
        mocker.patch("plate.config._CONFIG_PATH", Path("/nonexistent/config.toml"))
        cfg = load()
        assert cfg == {}

    def test_load_valid_config(self, mocker, tmp_path: Path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            '[export]\noutput_root = "/shots"\nproxy_max_width = 1280\n'
        )
        mocker.patch("plate.config._CONFIG_PATH", config_path)
        cfg = load()
        assert cfg["export"]["output_root"] == "/shots"
        assert cfg["export"]["proxy_max_width"] == 1280

    def test_load_invalid_toml_returns_empty(self, mocker, tmp_path: Path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("not valid toml {{{")
        mocker.patch("plate.config._CONFIG_PATH", config_path)
        cfg = load()
        assert cfg == {}


class TestMerge:
    def test_merge_uses_config_value_when_present(self):
        config = {"export": {"proxy_max_width": 640}}
        cmdline = {"proxy_max_width": 1920}
        merged = merge(config, cmdline)
        assert merged["proxy_max_width"] == 640

    def test_merge_keeps_cmdline_default_for_missing_config_key(self):
        config = {"export": {}}
        cmdline = {"proxy_max_width": 1920}
        merged = merge(config, cmdline)
        assert merged["proxy_max_width"] == 1920

    def test_merge_ignores_unrelated_keys(self):
        config = {"export": {"proxy_max_width": 640}}
        cmdline = {"proxy_max_width": 1920, "something_else": "value"}
        merged = merge(config, cmdline)
        assert merged["something_else"] == "value"
