"""Thin wrapper around ffmpeg.

Plate does not reimplement transcoding — it just builds ffmpeg command
lines for the two artifacts a plate-prep pipeline needs (an EXR sequence
and a scrub-friendly proxy) and shells out.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.frame_range import FrameRange

if TYPE_CHECKING:
    from ..color import ColorTransform


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


@contextlib.contextmanager
def _lut_context(color_transform: "ColorTransform | None"):
    """Context manager that yields the resolved .cube path, or None."""
    if color_transform is None or not color_transform.is_active():
        yield None
        return
    from ..color import bake_to_cube
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield bake_to_cube(color_transform, tmp_dir)


def export_exr_sequence(
    source_path: str | Path,
    frame_range: FrameRange,
    fps: float,
    exr_dir: str | Path,
    shot_name: str,
    pixel_format: str = "gbrpf32le",
    compression: str = "zip1",
    frame_padding: int = 6,
    color_transform: "ColorTransform | None" = None,
) -> int:
    """Export an EXR sequence covering frame_range.in_frame..out_frame.

    Files are named '{shot_name}.%0{padding}d.exr' with numbering matching
    the source's original frame numbers (via -start_number).

    Returns:
        The number of frames exported.
    """
    _check_binary()
    exr_dir = Path(exr_dir)
    exr_dir.mkdir(parents=True, exist_ok=True)

    seek = frame_range.seek_offset_seconds(fps)
    duration = frame_range.duration_seconds(fps)
    pattern = exr_dir / f"{shot_name}.%0{frame_padding}d.exr"

    with _lut_context(color_transform) as cube_path:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_path),
            "-ss", f"{seek:.6f}",
            "-t", f"{duration:.6f}",
        ]
        if cube_path is not None:
            cmd += ["-vf", f"lut3d={cube_path}"]
        cmd += [
            "-compression", compression,
            "-pix_fmt", pixel_format,
            "-start_number", str(frame_range.in_frame),
            str(pattern),
        ]
        _run(cmd)

    return frame_range.frame_count


def export_png_sequence(
    source_path: str | Path,
    frame_range: FrameRange,
    fps: float,
    png_dir: str | Path,
    shot_name: str,
    max_width: int = 1024,
    frame_padding: int = 6,
    color_transform: "ColorTransform | None" = None,
) -> int:
    """Export a 16-bit PNG sequence covering frame_range.in_frame..out_frame,
    scaled down if wider than max_width (never scaled up).

    Intended for display-referred deliveries (e.g. ComfyUI): the caller's
    color_transform — typically an OCIO display/view bake — is applied via
    lut3d after scaling. FFmpeg decodes the source with no color management,
    so the transform's declared input space must match the footage.

    Files are named '{shot_name}.%0{padding}d.png' with numbering matching
    the source's original frame numbers (via -start_number).

    Returns:
        The number of frames exported.
    """
    _check_binary()
    png_dir = Path(png_dir)
    png_dir.mkdir(parents=True, exist_ok=True)

    seek = frame_range.seek_offset_seconds(fps)
    duration = frame_range.duration_seconds(fps)
    pattern = png_dir / f"{shot_name}.%0{frame_padding}d.png"

    with _lut_context(color_transform) as cube_path:
        # Scale first (fewer pixels through the LUT); force a 16-bit
        # intermediate so filter negotiation never drops to 8-bit before
        # the lut3d runs.
        vf = f"scale='min({max_width},iw)':-2"
        if cube_path is not None:
            vf += f",format=rgb48le,lut3d={cube_path}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_path),
            "-ss", f"{seek:.6f}",
            "-t", f"{duration:.6f}",
            "-vf", vf,
            "-pix_fmt", "rgb48be",
            "-start_number", str(frame_range.in_frame),
            str(pattern),
        ]
        _run(cmd)

    return frame_range.frame_count


def _build_proxy_filter_graph(
    max_width: int,
    source_name: str,
    burn_in: list[str] | None = None,
) -> str:
    segments = [f"scale='min({max_width},iw)':-2"]

    if burn_in:
        for kind in burn_in:
            if kind == "frame_number":
                segments.append(
                    "drawtext=text='Frame %{frame_num}':"
                    "fontsize=24:fontcolor=white:x=10:y=10"
                )
            elif kind == "source_name":
                segments.append(
                    f"drawtext=text='{source_name}':"
                    "fontsize=24:fontcolor=white:x=10:y=h-th-32"
                )
            elif kind == "timecode":
                segments.append(
                    "drawtext=text='%{pts:hms}':"
                    "fontsize=24:fontcolor=white:x=10:y=h-th-64"
                )

    return ",".join(segments)


def export_proxy(
    source_path: str | Path,
    frame_range: FrameRange,
    fps: float,
    proxy_path: str | Path,
    max_width: int = 1920,
    video_codec: str = "libx264",
    crf: int = 18,
    color_transform: "ColorTransform | None" = None,
    burn_in: list[str] | None = None,
) -> Path:
    """Export a lightweight, scrub-friendly H.264 proxy covering the same
    IN/OUT selection as the EXR sequence, scaled down if wider than
    max_width (never scaled up).

    If ``color_transform`` is active, the LUT/OCIO transform is baked into
    the proxy via ffmpeg's lut3d filter, chained after scaling and burn-in.

    If ``burn_in`` is provided, drawtext filters are inserted for each
    requested overlay (frame_number, timecode, source_name).
    """
    _check_binary()
    proxy_path = Path(proxy_path)
    proxy_path.parent.mkdir(parents=True, exist_ok=True)

    seek = frame_range.seek_offset_seconds(fps)
    duration = frame_range.duration_seconds(fps)

    base_vf = _build_proxy_filter_graph(max_width, Path(source_path).name, burn_in)

    with _lut_context(color_transform) as cube_path:
        if cube_path is not None:
            vf = f"{base_vf},lut3d={cube_path}"
        else:
            vf = base_vf

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{seek:.6f}",
            "-i", str(source_path),
            "-t", f"{duration:.6f}",
            "-vf", vf,
            "-c:v", video_codec,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-an",
            str(proxy_path),
        ]
        _run(cmd)
    return proxy_path
