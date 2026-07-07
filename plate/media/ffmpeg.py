"""Thin wrapper around ffmpeg.

Plate does not reimplement transcoding — it just builds ffmpeg command
lines for the two artifacts a plate-prep pipeline needs (an EXR sequence
and a scrub-friendly proxy) and shells out.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..models.frame_range import FrameRange


class FFmpegError(RuntimeError):
    """Raised when ffmpeg fails or is not installed."""


def _check_binary() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError(
            "'ffmpeg' was not found on PATH. Install FFmpeg "
            "(https://ffmpeg.org/download.html) and make sure 'ffmpeg' "
            "is available in your shell."
        )


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise FFmpegError(
            f"ffmpeg command failed:\n  {' '.join(cmd)}\n\n{exc.stderr.strip()}"
        ) from exc


def export_exr_sequence(
    source_path: str | Path,
    frame_range: FrameRange,
    fps: float,
    exr_dir: str | Path,
    shot_name: str,
    pixel_format: str = "gbrpf32le",
) -> int:
    """Export an EXR sequence covering frame_range.in_frame..out_frame.

    Files are named '{shot_name}.{frame:06d}.exr' with numbering matching
    the source's original frame numbers (via -start_number).

    Returns:
        The number of frames exported.
    """
    _check_binary()
    exr_dir = Path(exr_dir)
    exr_dir.mkdir(parents=True, exist_ok=True)

    seek = frame_range.seek_offset_seconds(fps)
    duration = frame_range.duration_seconds(fps)
    pattern = exr_dir / f"{shot_name}.%06d.exr"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_path),
        "-ss", f"{seek:.6f}",
        "-t", f"{duration:.6f}",
        "-pix_fmt", pixel_format,
        "-start_number", str(frame_range.in_frame),
        str(pattern),
    ]
    _run(cmd)
    return frame_range.frame_count


def export_proxy(
    source_path: str | Path,
    frame_range: FrameRange,
    fps: float,
    proxy_path: str | Path,
    max_width: int = 1920,
    video_codec: str = "libx264",
    crf: int = 18,
) -> Path:
    """Export a lightweight, scrub-friendly H.264 proxy covering the same
    IN/OUT selection as the EXR sequence, scaled down if wider than
    max_width (never scaled up).
    """
    _check_binary()
    proxy_path = Path(proxy_path)
    proxy_path.parent.mkdir(parents=True, exist_ok=True)

    seek = frame_range.seek_offset_seconds(fps)
    duration = frame_range.duration_seconds(fps)
    scale_filter = f"scale='min({max_width},iw)':-2"

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{seek:.6f}",
        "-i", str(source_path),
        "-t", f"{duration:.6f}",
        "-vf", scale_filter,
        "-c:v", video_codec,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(proxy_path),
    ]
    _run(cmd)
    return proxy_path
