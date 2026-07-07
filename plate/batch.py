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
    lut_path: Optional[str | Path] = None
    ocio_config: Optional[str | Path] = None
    ocio_src: Optional[str] = None
    ocio_dst: Optional[str] = None
    burn_in: Optional[list[str]] = None


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
            lut_path=item.get("lut"),
            ocio_config=item.get("ocio_config"),
            ocio_src=item.get("ocio_src"),
            ocio_dst=item.get("ocio_dst"),
            burn_in=item.get("burn_in"),
        ))

    return entries


def _resolve_color(entry: BatchEntry) -> ColorTransform:
    """Build a ColorTransform from a BatchEntry's optional color fields."""
    try:
        return ColorTransform.from_options(
            lut_path=entry.lut_path,
            ocio_config=entry.ocio_config,
            ocio_src=entry.ocio_src,
            ocio_dst=entry.ocio_dst,
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
            color_transform = _resolve_color(entry)

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
                color_transform=color_transform,
                burn_in=entry.burn_in,
            )

            result = pipeline.run(progress=lambda msg, _pct=None: progress(f"  {msg}"))
            results.append(BatchResult(entry=entry, result=result))

        except Exception as exc:
            progress(f"  FAILED: {exc}")
            results.append(BatchResult(entry=entry, error=exc))

    return results
