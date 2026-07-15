"""Batch mode — run PlatePipeline against multiple sources in one invocation.

This module is deliberately free of CLI concerns so the GUI can import it
later without pulling in argparse or sys.argv.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .color import ColorTransform
from .pipeline import PlatePipeline, PipelineResult


@dataclass
class BatchEntry:
    """One clip in a batch run.

    `source`, `in_frame`, `out_frame` are required.
    All other fields are optional per-entry overrides that fall back to
    the global CLI defaults.
    """
    source: str | Path
    in_frame: int
    out_frame: int
    start_frame: Optional[int] = None
    output_root: Optional[str | Path] = None
    proxy_max_width: Optional[int] = None
    exr_pixel_format: Optional[str] = None
    exr_compression: Optional[str] = None
    frame_padding: Optional[int] = None
    skip_exr: Optional[bool] = None
    skip_proxy: Optional[bool] = None
    export_nuke_script: Optional[bool] = None
    lut_path: Optional[str | Path] = None
    ocio_config: Optional[str | Path] = None
    ocio_src: Optional[str] = None
    ocio_dst: Optional[str] = None
    ocio_display: Optional[str] = None
    ocio_view: Optional[str] = None
    burn_in: Optional[list[str]] = None
    comfy: Optional[bool] = None
    comfy_max_width: Optional[int] = None
    shot: Optional[str] = None
    shot_version: Optional[int] = None


@dataclass
class BatchResult:
    """Outcome of processing one batch entry."""
    entry: BatchEntry
    result: Optional[PipelineResult] = None
    error: Optional[Exception] = None


def load_batch_file(path: str | Path) -> list[BatchEntry]:
    """Parse a JSON batch file into a list of BatchEntry objects.

    The JSON file must be a list of objects. Each object must include
    ``source``, ``in``, and ``out`` keys. All other keys are optional.
    """
    path = Path(path)
    with open(path, "r") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("Batch file must contain a JSON array of entries.")

    entries: list[BatchEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {i} is not a JSON object.")

        source = item.get("source")
        in_frame = item.get("in")
        out_frame = item.get("out")

        if not source:
            raise ValueError(f"Entry {i}: missing required 'source' field.")
        if in_frame is None:
            raise ValueError(f"Entry {i}: missing required 'in' field.")
        if out_frame is None:
            raise ValueError(f"Entry {i}: missing required 'out' field.")

        entries.append(BatchEntry(
            source=source,
            in_frame=in_frame,
            out_frame=out_frame,
            start_frame=item.get("start_frame"),
            output_root=item.get("output"),
            proxy_max_width=item.get("proxy_width"),
            exr_pixel_format=item.get("exr_pixfmt"),
            exr_compression=item.get("exr_codec"),
            frame_padding=item.get("frame_padding"),
            skip_exr=item.get("skip_exr"),
            skip_proxy=item.get("skip_proxy"),
            export_nuke_script=item.get("nuke_script"),
            lut_path=item.get("lut"),
            ocio_config=item.get("ocio_config"),
            ocio_src=item.get("ocio_src"),
            ocio_dst=item.get("ocio_dst"),
            ocio_display=item.get("ocio_display"),
            ocio_view=item.get("ocio_view"),
            burn_in=item.get("burn_in"),
            comfy=item.get("comfy"),
            comfy_max_width=item.get("comfy_width"),
            shot=item.get("shot"),
            shot_version=item.get("shot_version"),
        ))

    return entries


def _resolve_color(
    entry: BatchEntry,
    ocio_display: Optional[str] = None,
    ocio_view: Optional[str] = None,
) -> ColorTransform:
    """Build a ColorTransform from a BatchEntry's optional color fields."""
    # Display/view given without ocio_dst means the OCIO options describe
    # the ComfyUI display bake only — the main transform stays inactive.
    display_only = ocio_display is not None and entry.ocio_dst is None
    try:
        return ColorTransform.from_options(
            lut_path=entry.lut_path,
            ocio_config=None if display_only else entry.ocio_config,
            ocio_src=None if display_only else entry.ocio_src,
            ocio_dst=entry.ocio_dst,
        )
    except ValueError as exc:
        raise ValueError(f"Entry '{entry.source}': {exc}")


def _resolve_comfy_color(
    entry: BatchEntry,
    fallback: ColorTransform,
    default_display: Optional[str] = None,
    default_view: Optional[str] = None,
) -> ColorTransform:
    """Color transform for the ComfyUI PNG export of one batch entry.

    Uses the entry's (or global default) display/view when given, otherwise
    falls back to the entry's main color transform.
    """
    display = entry.ocio_display if entry.ocio_display is not None else default_display
    view = entry.ocio_view if entry.ocio_view is not None else default_view
    if display is None and view is None:
        return fallback
    try:
        return ColorTransform.from_options(
            ocio_config=entry.ocio_config,
            ocio_src=entry.ocio_src,
            ocio_display=display,
            ocio_view=view,
        )
    except ValueError as exc:
        raise ValueError(f"Entry '{entry.source}': {exc}")


def run_batch(
    entries: list[BatchEntry],
    defaults: dict[str, Any],
    progress: Callable[[str], None] = print,
) -> list[BatchResult]:
    """Run PlatePipeline for each entry, collecting results.

    A failing clip never aborts the batch. Errors are collected per-entry
    and returned in ``BatchResult.error``.

    Parameters
    ----------
    entries:
        Parsed batch entries.
    defaults:
        Global fallback values. Keys matching ``PlatePipeline.__init__``
        parameter names are used when the entry does not supply a value.
        Expected keys: ``output_root``, ``start_frame``, ``proxy_max_width``,
        ``exr_pixel_format``, ``exr_compression``, ``frame_padding``,
        ``skip_exr``, ``skip_proxy``.
    progress:
        Called for each status update with a short string.

    Returns
    -------
    list[BatchResult]
        One result per entry, in the same order as ``entries``.
    """
    results: list[BatchResult] = []

    for idx, entry in enumerate(entries, 1):
        progress(f"[{idx}/{len(entries)}] Processing {entry.source}...")

        try:
            default_display = defaults.get("ocio_display")
            default_view = defaults.get("ocio_view")
            effective_display = (
                entry.ocio_display if entry.ocio_display is not None else default_display
            )
            effective_view = (
                entry.ocio_view if entry.ocio_view is not None else default_view
            )
            color_transform = _resolve_color(
                entry, ocio_display=effective_display, ocio_view=effective_view
            )

            export_comfy = (
                entry.comfy if entry.comfy is not None
                else defaults.get("export_comfy", False)
            )
            comfy_color_transform = None
            if export_comfy:
                comfy_color_transform = _resolve_comfy_color(
                    entry,
                    fallback=color_transform,
                    default_display=default_display,
                    default_view=default_view,
                )

            pipeline = PlatePipeline(
                source=entry.source,
                in_frame=entry.in_frame,
                out_frame=entry.out_frame,
                start_frame=entry.start_frame if entry.start_frame is not None else defaults.get("start_frame"),
                output_root=entry.output_root if entry.output_root is not None else defaults.get("output_root"),
                proxy_max_width=entry.proxy_max_width if entry.proxy_max_width is not None else defaults.get("proxy_max_width", 1920),
                exr_pixel_format=entry.exr_pixel_format if entry.exr_pixel_format is not None else defaults.get("exr_pixel_format", "gbrpf32le"),
                exr_compression=entry.exr_compression if entry.exr_compression is not None else defaults.get("exr_compression", "zip1"),
                frame_padding=entry.frame_padding if entry.frame_padding is not None else defaults.get("frame_padding", 6),
                skip_exr=entry.skip_exr if entry.skip_exr is not None else defaults.get("skip_exr", False),
                skip_proxy=entry.skip_proxy if entry.skip_proxy is not None else defaults.get("skip_proxy", False),
                export_nuke_script=entry.export_nuke_script if entry.export_nuke_script is not None else defaults.get("export_nuke_script", False),
                color_transform=color_transform,
                burn_in=entry.burn_in,
                export_comfy=export_comfy,
                comfy_max_width=entry.comfy_max_width if entry.comfy_max_width is not None else defaults.get("comfy_max_width", 1024),
                comfy_color_transform=comfy_color_transform,
                shot=entry.shot,
                shot_version=entry.shot_version,
            )

            result = pipeline.run(progress=lambda msg, _pct=None: progress(f"  {msg}"))
            results.append(BatchResult(entry=entry, result=result))

        except Exception as exc:
            progress(f"  FAILED: {exc}")
            results.append(BatchResult(entry=entry, error=exc))

    return results
