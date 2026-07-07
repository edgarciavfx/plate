"""FrameRange — the artist's IN/OUT selection.

This is the one genuinely differentiating piece of Plate: visual
frame-range selection. Everything downstream (export, proxy, manifest)
is just acting on this small, explicit object.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrameRange:
    start_frame: int
    in_frame: int
    out_frame: int

    def __post_init__(self) -> None:
        if self.in_frame < self.start_frame:
            raise ValueError(
                f"in_frame ({self.in_frame}) cannot be before "
                f"start_frame ({self.start_frame})"
            )
        if self.out_frame < self.in_frame:
            raise ValueError(
                f"out_frame ({self.out_frame}) cannot be before "
                f"in_frame ({self.in_frame})"
            )

    @property
    def frame_count(self) -> int:
        """Inclusive frame count between IN and OUT."""
        return self.out_frame - self.in_frame + 1

    def seek_offset_seconds(self, fps: float) -> float:
        """Seconds from the start of the file to the IN frame, for -ss."""
        return (self.in_frame - self.start_frame) / fps

    def duration_seconds(self, fps: float) -> float:
        """Duration in seconds covering IN through OUT, inclusive."""
        return self.frame_count / fps
