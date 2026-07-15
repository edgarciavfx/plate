"""Project/shot scaffolding — the folder structure and naming convention
a VFX shot lives in.

Shot mode lays out one folder per shot with task subfolders and versions
every artifact as ``{shot}_v{NNN}``:

    shots/img01_env/
    ├── ref/  comfy/  paint/  nuke/  renders/  breakdown/
    ├── plates/img01_env_v001/img01_env_v001.%06d.exr
    ├── comfy/img01_env_v001/img01_env_v001.%06d.png
    ├── nuke/img01_env_v001.nk
    ├── proxy_v001.mp4
    └── manifest.json

This module is deliberately dependency-free (stdlib only) so config,
models and pipeline can all import it without cycles.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_SHOT_FOLDERS = [
    "ref",
    "comfy",
    "paint",
    "nuke",
    "renders",
    "breakdown",
    "plates",
]

_SHOT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_PROXY_VERSION_RE = re.compile(r"^proxy_v(\d+)\.mp4$")


def versioned_name(shot: str, version: int) -> str:
    return f"{shot}_v{version:03d}"


def scaffold_shot(
    root: str | Path,
    shot_name: str,
    folders: list[str] | None = None,
) -> Path:
    """Create the shot folder structure under root and return the shot dir.

    Idempotent: existing folders are left untouched.
    """
    if not _SHOT_NAME_RE.match(shot_name):
        raise ValueError(
            f"Invalid shot name {shot_name!r}: use letters, digits, "
            "'_', '-' or '.' (no path separators)."
        )
    shot_dir = Path(root) / shot_name
    shot_dir.mkdir(parents=True, exist_ok=True)
    for folder in folders if folders is not None else DEFAULT_SHOT_FOLDERS:
        (shot_dir / folder).mkdir(parents=True, exist_ok=True)
    return shot_dir


def next_version(shot_dir: str | Path, shot_name: str) -> int:
    """Return the next free version number for a shot.

    Scans existing versioned artifacts (plates/comfy sequence dirs,
    nuke scripts, proxies) and returns max + 1, or 1 for a fresh shot.
    """
    shot_dir = Path(shot_dir)
    name_re = re.compile(rf"^{re.escape(shot_name)}_v(\d+)")
    found: list[int] = []

    for sub in ("plates", "comfy", "nuke"):
        folder = shot_dir / sub
        if not folder.is_dir():
            continue
        for entry in folder.iterdir():
            m = name_re.match(entry.name)
            if m:
                found.append(int(m.group(1)))

    if shot_dir.is_dir():
        for entry in shot_dir.iterdir():
            m = _PROXY_VERSION_RE.match(entry.name)
            if m:
                found.append(int(m.group(1)))

    return max(found) + 1 if found else 1


def resolve_folders(config: dict | None) -> list[str]:
    """Folder set for a shot: [project] folders from config, else default."""
    folders = (config or {}).get("project", {}).get("folders")
    if isinstance(folders, list) and all(isinstance(f, str) for f in folders):
        return list(folders)
    return list(DEFAULT_SHOT_FOLDERS)
