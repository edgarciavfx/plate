"""VideoMetadata — everything FFprobe can tell us about a source clip."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VideoMetadata:
    """Structured, typed view over raw ffprobe output.

    This is intentionally a thin, explicit model rather than a passthrough
    of ffprobe's raw JSON — Plate only cares about the fields that matter
    for plate prep, and normalizes them into consistent types/units.
    """

    path: str
    duration_seconds: float
    fps: float
    width: int
    height: int
    codec_name: str
    pixel_format: Optional[str] = None
    colorspace: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    bit_depth: Optional[int] = None
    has_audio: bool = False
    audio_codec: Optional[str] = None
    start_timecode: Optional[str] = None
    total_frames: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serializable view used by ManifestWriter (excludes raw ffprobe dump)."""
        return {
            "path": self.path,
            "duration_seconds": self.duration_seconds,
            "fps": round(self.fps, 3),
            "width": self.width,
            "height": self.height,
            "codec_name": self.codec_name,
            "pixel_format": self.pixel_format,
            "colorspace": self.colorspace,
            "color_transfer": self.color_transfer,
            "color_primaries": self.color_primaries,
            "bit_depth": self.bit_depth,
            "has_audio": self.has_audio,
            "audio_codec": self.audio_codec,
            "start_timecode": self.start_timecode,
            "total_frames": self.total_frames,
        }
