"""Command-line entry point for Plate.

Usage:
    python -m plate.cli SOURCE --in IN_FRAME --out OUT_FRAME [options]

Example:
    python -m plate.cli plate.mov --in 1204 --out 1389 \\
        --start-frame 1001 --output ./shots
"""

from __future__ import annotations

import argparse
import sys

from .media.ffprobe import FFprobeError
from .media.ffmpeg import FFmpegError
from .pipeline import PlatePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plate",
        description=(
            "Convert raw footage into an EXR sequence, a scrub proxy, "
            "and a metadata manifest, using FFmpeg/FFprobe under the hood."
        ),
    )
    parser.add_argument("source", help="Path to the source video file.")
    parser.add_argument(
        "--in", dest="in_frame", type=int, required=True,
        help="IN frame number (inclusive).",
    )
    parser.add_argument(
        "--out", dest="out_frame", type=int, required=True,
        help="OUT frame number (inclusive).",
    )
    parser.add_argument(
        "--start-frame", dest="start_frame", type=int, default=None,
        help="Frame number of the first frame in the source file "
             "(default: 0). Set this to match your source's embedded "
             "timecode/frame numbering, e.g. 1001.",
    )
    parser.add_argument(
        "--output", dest="output_root", default="./output",
        help="Root output directory (default: ./output). A subfolder "
             "named after the source file will be created inside it.",
    )
    parser.add_argument(
        "--proxy-width", dest="proxy_max_width", type=int, default=1920,
        help="Max width for the proxy (default: 1920). Never scales up.",
    )
    parser.add_argument(
        "--exr-pixfmt", dest="exr_pixel_format", default="gbrpf32le",
        help="Pixel format for EXR export (default: gbrpf32le, "
             "32-bit float linear).",
    )
    parser.add_argument(
        "--skip-exr", action="store_true",
        help="Skip EXR sequence generation.",
    )
    parser.add_argument(
        "--skip-proxy", action="store_true",
        help="Skip proxy generation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline = PlatePipeline(
        source=args.source,
        in_frame=args.in_frame,
        out_frame=args.out_frame,
        output_root=args.output_root,
        start_frame=args.start_frame,
        proxy_max_width=args.proxy_max_width,
        exr_pixel_format=args.exr_pixel_format,
        skip_exr=args.skip_exr,
        skip_proxy=args.skip_proxy,
    )

    try:
        pipeline.run(progress=lambda msg: print(f"[plate] {msg}"))
    except FileNotFoundError as exc:
        print(f"[plate] error: {exc}", file=sys.stderr)
        return 1
    except (FFprobeError, FFmpegError) as exc:
        print(f"[plate] error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[plate] invalid frame range: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
