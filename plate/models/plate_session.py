"""PlateSession — a single unit of work: one source clip, one selection,
one destination folder, and the resulting artifacts once processed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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

    def __post_init__(self) -> None:
        self.source_path = Path(self.source_path)
        self.output_dir = Path(self.output_dir)

    @property
    def shot_name(self) -> str:
        return self.source_path.stem

    def ensure_output_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.exr_dir = self.output_dir / "exr"
        self.exr_dir.mkdir(parents=True, exist_ok=True)
