"""Thumbnail extraction — extract evenly-spaced frame thumbnails from a
source video using ffmpeg, for display on the Timeline ruler.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


_CACHE_DIR = Path.home() / ".plate" / "cache" / "thumbnails"


def _source_cache_key(source: str | Path, frame_interval: int) -> str:
    """Generate a deterministic cache key based on source path + interval."""
    raw = f"{Path(source).resolve()}::{frame_interval}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def extract_thumbnails(
    source: str | Path,
    total_frames: int,
    thumb_count: int = 20,
    frame_interval: Optional[int] = None,
    thumb_width: int = 160,
) -> list[tuple[int, str]]:
    """Extract evenly-spaced thumbnails from *source*.

    Parameters
    ----------
    source:
        Path to the source video.
    total_frames:
        Total number of frames in the source.
    thumb_count:
        Number of thumbnails to extract (used when *frame_interval* is not set).
    frame_interval:
        Extract every Nth frame. Overrides *thumb_count*.
    thumb_width:
        Width of each thumbnail in pixels.

    Returns
    -------
    list[tuple[int, str]]
        Sorted list of ``(frame_number, thumbnail_path)`` tuples.
    """
    source = Path(source)
    if not source.exists():
        return []

    interval = frame_interval or max(1, total_frames // thumb_count)
    if interval <= 0:
        interval = 1

    cache_key = _source_cache_key(source, interval)
    cache_dir = _CACHE_DIR / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)

    existing = _load_cached(cache_dir)
    if existing:
        return existing

    tmp_dir = Path(tempfile.mkdtemp(prefix="plate_thumbs_"))
    pattern = str(tmp_dir / "%04d.jpg")

    select_expr = f"not(mod(n\\,{interval}))"
    cmd = [
        "ffmpeg",
        "-i", str(source),
        "-vf", f"select='{select_expr}',scale={thumb_width}:-1",
        "-vsync", "vfr",
        "-qscale:v", "5",
        "-y",
        pattern,
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        _cleanup(tmp_dir)
        return []

    thumbnails: list[tuple[int, str]] = []
    for p in sorted(tmp_dir.iterdir()):
        if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            seq_index = int(p.stem)
            frame = seq_index * interval
            dest = cache_dir / p.name
            shutil.move(p, dest)
            thumbnails.append((frame, str(dest)))

    _cleanup(tmp_dir)

    thumbnails.sort(key=lambda t: t[0])
    _save_index(cache_dir, thumbnails)
    return thumbnails


def clear_cache() -> None:
    """Remove all cached thumbnails."""
    if _CACHE_DIR.exists():
        import shutil
        shutil.rmtree(_CACHE_DIR)


def _load_cached(cache_dir: Path) -> list[tuple[int, str]]:
    index_path = cache_dir / "index.txt"
    if not index_path.exists():
        return []
    thumbnails: list[tuple[int, str]] = []
    for line in index_path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            frame_str, path_str = parts
            p = Path(path_str)
            if p.exists():
                try:
                    thumbnails.append((int(frame_str), str(p)))
                except ValueError:
                    continue
    return thumbnails


def _save_index(cache_dir: Path, thumbnails: list[tuple[int, str]]) -> None:
    lines = [f"{frame} {path}" for frame, path in thumbnails]
    (cache_dir / "index.txt").write_text("\n".join(lines))


def _cleanup(tmp_dir: Path) -> None:
    import shutil
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
