"""PlateSession — a single unit of work: one source clip, one selection,
one destination folder, and the resulting artifacts once processed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..project import scaffold_shot, versioned_name
from .frame_range import FrameRange
from .video_metadata import VideoMetadata


@dataclass
class PlateSession:
    source_path: Path
    output_dir: Path
    frame_range: FrameRange

    metadata: Optional[VideoMetadata] = None
    exr_dir: Optional[Path] = None
    proxy_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    exported_frames: int = 0
    color_transform: Optional[object] = None  # ColorTransform, avoided circular import
    comfy_dir: Optional[Path] = None
    comfy_pattern: Optional[str] = None
    comfy_frames: int = 0
    comfy_max_width: int = 0
    comfy_color_transform: Optional[object] = None  # ColorTransform
    shot: Optional[str] = None
    version: int = 1

    def __post_init__(self) -> None:
        self.source_path = Path(self.source_path)
        self.output_dir = Path(self.output_dir)

    @property
    def shot_mode(self) -> bool:
        return self.shot is not None

    @property
    def shot_name(self) -> str:
        if self.shot is not None:
            return self.shot
        return self.source_path.stem

    @property
    def versioned_name(self) -> Optional[str]:
        if self.shot is None:
            return None
        return versioned_name(self.shot, self.version)

    @property
    def frame_base_name(self) -> str:
        """Base name for per-frame files (EXRs, PNGs)."""
        return self.versioned_name or self.source_path.stem

    @property
    def plates_dir(self) -> Path:
        if self.shot_mode:
            return self.output_dir / "plates" / self.frame_base_name
        return self.output_dir / "exr"

    @property
    def comfy_export_dir(self) -> Path:
        if self.shot_mode:
            return self.output_dir / "comfy" / self.frame_base_name
        return self.output_dir / "comfy"

    @property
    def proxy_filename(self) -> str:
        if self.shot_mode:
            return f"proxy_v{self.version:03d}.mp4"
        return "proxy.mp4"

    @property
    def nuke_script_path(self) -> Path:
        if self.shot_mode:
            return self.output_dir / "nuke" / f"{self.frame_base_name}.nk"
        return self.output_dir / f"{self.shot_name}.nk"

    def ensure_output_dirs(self, scaffold_folders: Optional[list[str]] = None) -> None:
        if self.shot_mode:
            scaffold_shot(self.output_dir.parent, self.shot, scaffold_folders)
        else:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.exr_dir = self.plates_dir
        self.exr_dir.mkdir(parents=True, exist_ok=True)
