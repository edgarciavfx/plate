from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


_PRESET_PATH = Path.home() / ".plate" / "presets.toml"


@dataclass
class ExportPreset:
    name: str
    description: str = ""
    proxy_max_width: int = 1920
    exr_pixel_format: str = "gbrpf32le"
    exr_compression: str = "zip1"
    frame_padding: int = 6
    comfy: bool = False
    comfy_max_width: int = 1024

    def to_dict(self) -> dict[str, Any]:
        return {
            "proxy_max_width": self.proxy_max_width,
            "exr_pixel_format": self.exr_pixel_format,
            "exr_compression": self.exr_compression,
            "frame_padding": self.frame_padding,
            "comfy": self.comfy,
            "comfy_max_width": self.comfy_max_width,
        }


BUILTIN_PRESETS: dict[str, ExportPreset] = {
    "ACES 2K": ExportPreset(
        name="ACES 2K",
        description="2048-wide proxy, 32-bit float EXR, ACES workflow",
        proxy_max_width=2048,
        exr_pixel_format="gbrpf32le",
        exr_compression="zip1",
    ),
    "Rec709 HD": ExportPreset(
        name="Rec709 HD",
        description="1920-wide proxy, 16-bit half-float EXR, Rec709 delivery",
        proxy_max_width=1920,
        exr_pixel_format="gbrp16le",
        exr_compression="zip1",
    ),
    "Archival 4K": ExportPreset(
        name="Archival 4K",
        description="4096-wide proxy, 32-bit float EXR, maximum quality",
        proxy_max_width=4096,
        exr_pixel_format="gbrpf32le",
        exr_compression="none",
    ),
}


def load_user_presets() -> dict[str, ExportPreset]:
    if not _PRESET_PATH.exists():
        return {}
    try:
        raw = tomllib.loads(_PRESET_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    presets: dict[str, ExportPreset] = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            val["name"] = key
            try:
                presets[key] = ExportPreset(**val)
            except TypeError:
                continue
    return presets


def all_presets() -> dict[str, ExportPreset]:
    presets = dict(BUILTIN_PRESETS)
    presets.update(load_user_presets())
    return presets


def resolve_preset(name: str | None) -> dict[str, Any]:
    if name is None:
        return {}
    presets = all_presets()
    preset = presets.get(name)
    if preset is None:
        return {}
    return preset.to_dict()
