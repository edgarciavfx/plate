"""Command-line entry point for Plate.

Usage:
    python -m plate.cli SOURCE --in IN_FRAME --out OUT_FRAME [options]
    python -m plate.cli --batch BATCH_FILE [options]

Example:
    python -m plate.cli plate.mov --in 1204 --out 1389 \\
        --start-frame 1001 --output ./shots
    python -m plate.cli --batch batch.json --output ./shots
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("plate")

from . import __version__ as plate_version
from .batch import load_batch_file, run_batch
from .color import ColorTransform
from .config import load as load_config, merge as merge_config
from .presets import resolve_preset
from .project import resolve_folders, scaffold_shot
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
    parser.add_argument("source", nargs="?", help="Path to the source video file.")
    parser.add_argument("--batch", metavar="PATH", help="Path to a batch JSON file.")
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {plate_version}",
        help="Show version number and exit.",
    )
    parser.add_argument(
        "--in", dest="in_frame", type=int, default=None,
        help="IN frame number (inclusive). Required in single-clip mode.",
    )
    parser.add_argument(
        "--out", dest="out_frame", type=int, default=None,
        help="OUT frame number (inclusive). Required in single-clip mode.",
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
        "--exr-codec", dest="exr_compression", default="zip1",
        choices=["none", "rle", "zip1", "zip16"],
        help="EXR compression codec (default: zip1).",
    )
    parser.add_argument(
        "--frame-padding", dest="frame_padding", type=int, default=6,
        help="Zero-padding for EXR frame numbers (default: 6, e.g. %%06d).",
    )
    parser.add_argument(
        "--skip-exr", action="store_true",
        help="Skip EXR sequence generation.",
    )
    parser.add_argument(
        "--skip-proxy", action="store_true",
        help="Skip proxy generation.",
    )
    parser.add_argument(
        "--nuke-script", action="store_true",
        help="Generate a Nuke .nk script pointing at the EXR sequence.",
    )
    parser.add_argument(
        "--comfy", action="store_true",
        help="Also export a display-referred 16-bit PNG sequence (into a "
             "'comfy/' subfolder) for ComfyUI. Uses --ocio-display/--ocio-view "
             "if given, otherwise the main color transform.",
    )
    parser.add_argument(
        "--comfy-width", dest="comfy_max_width", type=int, default=1024,
        help="Max width for the ComfyUI PNGs (default: 1024). Never scales up.",
    )
    parser.add_argument(
        "--shot", default=None, metavar="NAME",
        help="Shot name (e.g. img01_env). Switches to the shot layout: "
             "ref/comfy/paint/nuke/renders/breakdown/plates task folders "
             "and versioned artifact names like img01_env_v001. Without "
             "it the classic source-named layout is used.",
    )
    parser.add_argument(
        "--shot-version", dest="shot_version", type=int, default=None,
        metavar="N",
        help="Force a specific version number (requires --shot). "
             "Default: the next free version is picked automatically.",
    )
    parser.add_argument(
        "--new-shot", dest="new_shot", default=None, metavar="NAME",
        help="Scaffold an empty shot folder structure under --output and "
             "exit (no source needed).",
    )
    parser.add_argument(
        "--preset", default=None, metavar="NAME",
        help="Export preset name (e.g. 'ACES 2K', 'Rec709 HD', 'Archival 4K'). "
             "Overrides individual defaults.",
    )
    parser.add_argument(
        "--burn-in", dest="burn_in", action="append", default=None,
        choices=["frame_number", "timecode", "source_name"],
        help="Overlay information on the proxy. Can be specified "
             "multiple times.",
    )

    color = parser.add_argument_group(
        "color transform",
        "Apply a color transform during EXR export (mutually exclusive options).",
    )
    color.add_argument(
        "--lut", dest="lut_path", default=None, metavar="PATH",
        help="Path to a .cube LUT file to apply during EXR export.",
    )
    color.add_argument(
        "--ocio-config", dest="ocio_config", default=None, metavar="PATH",
        help="Path to an OpenColorIO config.ocio file.",
    )
    color.add_argument(
        "--ocio-src", dest="ocio_src", default=None, metavar="NAME",
        help="Source colorspace name (requires --ocio-config).",
    )
    color.add_argument(
        "--ocio-dst", dest="ocio_dst", default=None, metavar="NAME",
        help="Destination colorspace name (requires --ocio-config).",
    )
    color.add_argument(
        "--ocio-display", dest="ocio_display", default=None, metavar="NAME",
        help="OCIO display name for the ComfyUI export "
             "(requires --ocio-config, --ocio-src and --ocio-view).",
    )
    color.add_argument(
        "--ocio-view", dest="ocio_view", default=None, metavar="NAME",
        help="OCIO view name for the ComfyUI export "
             "(requires --ocio-config, --ocio-src and --ocio-display).",
    )

    return parser


def _build_color_transform(args) -> ColorTransform | None:
    # When --ocio-display/--ocio-view are given without --ocio-dst, the OCIO
    # options describe the ComfyUI display bake only — the main EXR/proxy
    # transform stays inactive.
    display_only = args.ocio_display is not None and args.ocio_dst is None
    try:
        return ColorTransform.from_options(
            lut_path=args.lut_path,
            ocio_config=None if display_only else args.ocio_config,
            ocio_src=None if display_only else args.ocio_src,
            ocio_dst=args.ocio_dst,
        )
    except ValueError as exc:
        logger.error("error: %s", exc)
        return None


def _build_comfy_transform(args, fallback: ColorTransform) -> ColorTransform | None:
    """Color transform for the ComfyUI PNG export.

    With --ocio-display/--ocio-view, bakes that display/view transform;
    otherwise falls back to the main color transform (so e.g.
    ``--comfy --lut foo.cube`` bakes the same LUT into the PNGs).
    Returns None on invalid options.
    """
    if args.ocio_display is None and args.ocio_view is None:
        return fallback
    try:
        return ColorTransform.from_options(
            ocio_config=args.ocio_config,
            ocio_src=args.ocio_src,
            ocio_display=args.ocio_display,
            ocio_view=args.ocio_view,
        )
    except ValueError as exc:
        logger.error("error: %s", exc)
        return None


def _merge_config_into_args(args, parser) -> None:
    cfg = load_config()
    if not cfg:
        return
    export_cfg = cfg.get("export", {})
    for key in [
        "output_root", "proxy_max_width", "exr_pixel_format",
        "exr_compression", "frame_padding", "crf",
        "comfy", "comfy_max_width",
    ]:
        if key in export_cfg and getattr(args, key, None) == parser.get_default(key):
            setattr(args, key, export_cfg[key])


def _run_new_shot(args) -> int:
    """Scaffold an empty shot folder structure and exit."""
    try:
        shot_dir = scaffold_shot(
            args.output_root, args.new_shot, resolve_folders(load_config())
        )
    except (ValueError, OSError) as exc:
        logger.error("error: %s", exc)
        return 1
    logger.info("Shot scaffolded: %s", shot_dir)
    return 0


def _run_single(args, parser) -> int:
    """Process a single clip (legacy mode)."""
    _merge_config_into_args(args, parser)

    color_transform = _build_color_transform(args)
    if color_transform is None:
        return 1

    preset_values = resolve_preset(args.preset)
    for key in [
        "proxy_max_width", "exr_pixel_format", "exr_compression",
        "frame_padding", "comfy", "comfy_max_width",
    ]:
        if key in preset_values and getattr(args, key, None) == parser.get_default(key):
            setattr(args, key, preset_values[key])

    comfy_transform = None
    if args.comfy:
        comfy_transform = _build_comfy_transform(args, color_transform)
        if comfy_transform is None:
            return 1

    pipeline = PlatePipeline(
        source=args.source,
        in_frame=args.in_frame,
        out_frame=args.out_frame,
        output_root=args.output_root,
        start_frame=args.start_frame,
        proxy_max_width=args.proxy_max_width,
        exr_pixel_format=args.exr_pixel_format,
        exr_compression=getattr(args, "exr_compression", "zip1"),
        frame_padding=getattr(args, "frame_padding", 6),
        skip_exr=args.skip_exr,
        skip_proxy=args.skip_proxy,
        export_nuke_script=args.nuke_script,
        color_transform=color_transform,
        burn_in=args.burn_in,
        export_comfy=args.comfy,
        comfy_max_width=args.comfy_max_width,
        comfy_color_transform=comfy_transform,
        shot=args.shot,
        shot_version=args.shot_version,
    )

    try:
        pipeline.run(progress=lambda msg, _pct=None: logger.info("%s", msg))
    except FileNotFoundError as exc:
        logger.error("error: %s", exc)
        return 1
    except (FFprobeError, FFmpegError) as exc:
        logger.error("error: %s", exc)
        return 1
    except ValueError as exc:
        logger.error("invalid frame range: %s", exc)
        return 1
    except ImportError as exc:
        logger.error("error: %s", exc)
        return 1

    return 0


def _run_batch_mode(args, parser) -> int:
    """Load batch JSON and run all entries, printing a summary."""
    _merge_config_into_args(args, parser)

    try:
        entries = load_batch_file(args.batch)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        logger.error("error loading batch file: %s", exc)
        return 1

    if not entries:
        logger.error("batch file contains no entries.")
        return 1

    preset_values = resolve_preset(args.preset)
    defaults = {
        "output_root": args.output_root,
        "start_frame": args.start_frame,
        "proxy_max_width": preset_values.get("proxy_max_width", args.proxy_max_width),
        "exr_pixel_format": preset_values.get("exr_pixel_format", args.exr_pixel_format),
        "exr_compression": preset_values.get("exr_compression", getattr(args, "exr_compression", "zip1")),
        "frame_padding": preset_values.get("frame_padding", getattr(args, "frame_padding", 6)),
        "skip_exr": args.skip_exr,
        "skip_proxy": args.skip_proxy,
        "export_nuke_script": args.nuke_script,
        "export_comfy": preset_values.get("comfy", args.comfy),
        "comfy_max_width": preset_values.get("comfy_max_width", args.comfy_max_width),
        "ocio_display": args.ocio_display,
        "ocio_view": args.ocio_view,
    }

    results = run_batch(
        entries,
        defaults=defaults,
        progress=lambda msg, _pct=None: logger.info("%s", msg),
    )

    # Summary
    success_count = 0
    fail_count = 0
    for r in results:
        if r.error:
            fail_count += 1
        else:
            success_count += 1

    logger.info("Batch complete: %d succeeded, %d failed", success_count, fail_count)

    for r in results:
        if r.error:
            logger.error("[FAIL] %s: %s", Path(r.entry.source).name, r.error)

    return 1 if fail_count > 0 else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        format="[plate] %(message)s",
        level=logging.INFO,
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    # Mutual exclusion: source XOR --batch
    has_source = args.source is not None
    has_batch = args.batch is not None

    if args.new_shot is not None:
        if has_source or has_batch:
            logger.error("--new-shot only scaffolds folders; drop the source/--batch "
                         "(use --shot to export into a shot).")
            return 1
        return _run_new_shot(args)

    if args.shot_version is not None and args.shot is None:
        logger.error("--shot-version requires --shot.")
        return 1

    if args.shot is not None and has_batch:
        logger.error("--shot cannot be combined with --batch; "
                     "set a per-entry \"shot\" key in the batch file instead.")
        return 1

    if has_source and has_batch:
        logger.error("provide a source file OR --batch, not both.")
        return 1

    if not has_source and not has_batch:
        parser.print_usage()
        logger.error("a source file or --batch is required.")
        return 1

    if has_batch:
        return _run_batch_mode(args, parser)

    if args.in_frame is None or args.out_frame is None:
        logger.error("--in and --out are required in single-clip mode.")
        return 1

    return _run_single(args, parser)


if __name__ == "__main__":
    sys.exit(main())
