from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from .project import DEFAULT_SHOT_FOLDERS


_CONFIG_DIR = Path.home() / ".plate"
_CONFIG_PATH = _CONFIG_DIR / "config.toml"

EXPORT_DEFAULTS: dict[str, Any] = {
    "output_root": None,
    "proxy_max_width": 1920,
    "exr_pixel_format": "gbrpf32le",
    "exr_compression": "zip1",
    "frame_padding": 6,
    "crf": 18,
    "skip_exr": False,
    "skip_proxy": False,
    "burn_in": None,
    "comfy": False,
    "comfy_max_width": 1024,
}

PROJECT_DEFAULTS: dict[str, Any] = {
    "folders": list(DEFAULT_SHOT_FOLDERS),
}

COLOR_DEFAULTS: dict[str, Any] = {
    "lut_path": None,
    "ocio_config": None,
    "ocio_src": None,
    "ocio_dst": None,
    "ocio_display": None,
    "ocio_view": None,
}


def load() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        raw = _CONFIG_PATH.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def merge(config: dict[str, Any], cmdline_defaults: dict[str, Any]) -> dict[str, Any]:
    merged = dict(cmdline_defaults)
    export_cfg = config.get("export", {})
    for key in EXPORT_DEFAULTS:
        if key in export_cfg and export_cfg[key] is not None:
            merged[key] = export_cfg[key]
    return merged
