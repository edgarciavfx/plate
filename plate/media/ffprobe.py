"""Thin wrapper around ffprobe.

Plate does not reimplement metadata extraction — it just calls ffprobe,
parses its JSON, and normalizes the handful of fields plate prep cares
about into a VideoMetadata object.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..models.video_metadata import VideoMetadata


class FFprobeError(RuntimeError):
    """Raised when ffprobe fails or ffprobe/ffmpeg is not installed."""


def _check_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise FFprobeError(
            f"'{name}' was not found on PATH. Install FFmpeg "
            f"(https://ffmpeg.org/download.html) and make sure '{name}' "
            f"is available in your shell."
        )


def _parse_frame_rate(rate_str: str) -> float:
    """Parse ffprobe's 'num/den' frame rate strings (e.g. '24000/1001')."""
    if "/" in rate_str:
        num, den = rate_str.split("/")
        den = float(den)
        return float(num) / den if den else 0.0
    return float(rate_str)


def probe(source_path: str | Path) -> VideoMetadata:
    """Run ffprobe on source_path and return a VideoMetadata instance.

    Raises:
        FileNotFoundError: if source_path does not exist.
        FFprobeError: if ffprobe is missing or the file can't be read.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    _check_binary("ffprobe")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(source_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise FFprobeError(
            f"ffprobe failed on {source_path}: {exc.stderr.strip()}"
        ) from exc

    data = json.loads(result.stdout)

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None:
        raise FFprobeError(f"No video stream found in {source_path}")

    fps = _parse_frame_rate(
        video_stream.get("r_frame_rate")
        or video_stream.get("avg_frame_rate")
        or "24/1"
    )
    duration_seconds = float(
        video_stream.get("duration") or fmt.get("duration") or 0.0
    )

    total_frames = video_stream.get("nb_frames")
    if total_frames is not None:
        total_frames = int(total_frames)
    elif fps and duration_seconds:
        total_frames = round(duration_seconds * fps)

    bit_depth = None
    pix_fmt = video_stream.get("pix_fmt")
    if pix_fmt:
        for token in ("16", "12", "10", "8"):
            if token in pix_fmt:
                bit_depth = int(token)
                break

    tags = video_stream.get("tags", {}) or {}

    return VideoMetadata(
        path=str(source_path),
        duration_seconds=duration_seconds,
        fps=fps,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        codec_name=video_stream.get("codec_name", "unknown"),
        pixel_format=pix_fmt,
        colorspace=video_stream.get("color_space"),
        color_transfer=video_stream.get("color_transfer"),
        color_primaries=video_stream.get("color_primaries"),
        bit_depth=bit_depth,
        has_audio=audio_stream is not None,
        audio_codec=(audio_stream or {}).get("codec_name"),
        start_timecode=tags.get("timecode"),
        total_frames=total_frames,
        raw=data,
    )
