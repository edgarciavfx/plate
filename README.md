# Plate

A workflow layer on top of the FFmpeg toolchain, purpose-built for VFX
plate preparation.

Plate doesn't replace `ffmpeg`, `ffprobe`, or a media player — it
orchestrates them:

- **FFprobe answers questions about media.**
- **FFmpeg transforms media.**
- **Plate manages the artist's workflow.**

```
Open Footage -> Inspect -> Generate Proxy -> Generate EXRs
-> Generate Manifest -> Done
```

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) (provides both `ffmpeg` and
  `ffprobe`) available on your `PATH`
- `PySide6` — only required for the GUI (`pip install -r requirements.txt`).
  The CLI pipeline itself is stdlib + `subprocess` calls to FFmpeg, no
  third-party packages needed.

## Project layout

```
plate/
├── media/       ffprobe.py, ffmpeg.py       — thin wrappers, no workflow logic
├── models/      VideoMetadata, FrameRange, PlateSession
├── export/      ExportJob, ProxyJob, ManifestWriter
├── pipeline.py  PlatePipeline               — the end-to-end orchestration
├── cli.py       command-line entry point
├── ui/          PySide6 viewer (see below)
└── app.py       GUI entry point
```

The `ui/` package only ever configures and drives a `PlatePipeline`
through `SessionController` — it owns no ffmpeg/ffprobe logic itself.

## CLI usage

```bash
python -m plate.cli SOURCE --in IN_FRAME --out OUT_FRAME [options]
python -m plate.cli --batch BATCH_FILE [options]
```

### Example — single clip

```bash
python -m plate.cli plate.mov --in 1204 --out 1389 \
    --start-frame 1001 --output ./shots
```

This produces:

```
shots/
└── plate/
    ├── proxy.mp4
    ├── exr/
    │   ├── plate.001204.exr
    │   ├── plate.001205.exr
    │   └── ...
    └── manifest.json
```

### Options

| Flag               | Default         | Description                                       |
|--------------------|-----------------|----------------------------------------------------|
| `--in`              | required*       | IN frame number (inclusive)                        |
| `--out`             | required*       | OUT frame number (inclusive)                       |
| `--start-frame`     | `0`             | First frame number embedded in the source file     |
| `--output`          | `./output`      | Root output directory                              |
| `--proxy-width`     | `1920`          | Max proxy width (never scales up)                  |
| `--exr-pixfmt`      | `gbrpf32le`     | EXR pixel format (32-bit float linear)              |
| `--skip-exr`        | off             | Skip EXR sequence generation                        |
| `--skip-proxy`      | off             | Skip proxy generation                                |
| `--batch`           | —               | Path to a batch JSON file (see Batch mode below)   |

*\*Required in single-clip mode; not needed when using `--batch`.*

### Batch mode

Process multiple clips from a JSON file in a single invocation. Each clip
gets its own output subfolder under `--output`, just like single-clip mode.
One failing clip does not abort the batch — errors are collected and
printed in a summary at the end.

#### Batch JSON format

```json
[
  {
    "source": "plate_a.mov",
    "in": 1001,
    "out": 1100,
    "start_frame": 1001
  },
  {
    "source": "plate_b.mov",
    "in": 1204,
    "out": 1389,
    "start_frame": 1001,
    "proxy_width": 1280,
    "skip_proxy": true
  }
]
```

Required per-entry fields: **`source`**, **`in`**, **`out`**.

Optional per-entry overrides (fall back to the CLI global flags):
`start_frame`, `output`, `proxy_width`, `exr_pixfmt`, `skip_exr`,
`skip_proxy`, `lut`, `ocio_config`, `ocio_src`, `ocio_dst`.

#### Example

```bash
python -m plate.cli --batch jobs.json --output ./shots
```

Expected output:

```
[plate] [1/2] Processing plate_a.mov...
[plate]   Inspecting plate_a.mov...
[plate]   Generating proxy...
[plate]   Generating EXR sequence (100 frames)...
[plate]   Writing manifest...
[plate]   Done. Shot written to shots/plate_a
[plate] [2/2] Processing plate_b.mov...
[plate]   Inspecting plate_b.mov...
[plate]   Skipping EXR generation.
[plate]   Generating proxy...
[plate]   Writing manifest...
[plate]   Done. Shot written to shots/plate_b

[plate] ╔══════════════════════════════════════════════╗
[plate] ║            Batch Summary                     ║
[plate] ╠══════════════════════════════════════════════╣
[plate] ║  [ok  ] plate_a.mov                                     ║
[plate] ║  [ok  ] plate_b.mov                                     ║
[plate] ╠══════════════════════════════════════════════╣
[plate] ║  2 succeeded, 0 failed                       ║
[plate] ╚══════════════════════════════════════════════╝
```

Directory structure after a batch run:

```
shots/
├── plate_a/
│   ├── proxy.mp4
│   ├── exr/
│   │   ├── plate_a.001001.exr
│   │   └── ...
│   └── manifest.json
└── plate_b/
    ├── proxy.mp4
    ├── exr/
    │   ├── plate_b.001204.exr
    │   └── ...
    └── manifest.json
```

## manifest.json

```json
{
  "shot": "plate",
  "source": "plate.mov",
  "created_at": "2026-07-07T12:00:00+00:00",
  "start_frame": 1001,
  "in": 1204,
  "out": 1389,
  "exported_frames": 186,
  "proxy": "shots/plate/proxy.mp4",
  "exr_dir": "shots/plate/exr",
  "duration_seconds": 16.66,
  "fps": 23.976,
  "width": 4096,
  "height": 2160,
  "codec_name": "prores",
  "colorspace": "bt709",
  "bit_depth": 10,
  "has_audio": true
}
```

This manifest is designed to plug straight into downstream shot
ingestion, automation, or AI-assisted workflows without anyone needing
to re-derive metadata by hand.

## Using it as a library

```python
from plate.pipeline import PlatePipeline

pipeline = PlatePipeline(
    source="plate.mov",
    in_frame=1204,
    out_frame=1389,
    start_frame=1001,
    output_root="./shots",
)
result = pipeline.run()
print(result.manifest_path)
```

## GUI usage

```bash
pip install -r requirements.txt
python -m plate.app
```

Workflow: **Open** a clip (File → Open) → the file is probed
automatically and loaded into the viewer → scrub with the slider or
step frame-by-frame with the transport buttons → **Set IN** / **Set
OUT** at the playhead → **File → Export...** → choose output directory
and export options → export runs in the background while you keep
working, with progress shown in the status bar.

### GUI architecture

```
MainWindow
 ├── Viewer              QMediaPlayer/QVideoWidget wrapper — playback only
 ├── Scrubber            time-based (ms) slider, synced to Viewer position
 ├── Timeline            frame-based ruler — draggable IN/OUT handles (the
 │                       actual differentiating widget: visual frame-range
 │                       selection)
 ├── TransportControls   Play/Pause, step ±1 frame, Set IN, Set OUT
 ├── ExportDialog        collects output dir / proxy width / pixel format
 └── SessionController   the only class touching both Qt and Plate's core
                          (VideoMetadata, PlateSession, PlatePipeline);
                          converts frame numbers <-> milliseconds and runs
                          export on a background QThread so the UI never
                          blocks during EXR/proxy generation
```

Every other widget is intentionally "dumb" — they emit signals
(`seekRequested`, `setInClicked`, etc.) and hold no ffmpeg/ffprobe
knowledge. `SessionController` is the single seam between UI and core,
which is what keeps `PlatePipeline` usable identically from the CLI,
the GUI, or a future batch/automation script.

## Roadmap

### Done
- [x] `ffprobe` wrapper -> `VideoMetadata`
- [x] `ffmpeg` wrappers -> EXR sequence + proxy
- [x] `PlatePipeline` orchestration + manifest
- [x] CLI
- [x] PySide6 viewer (`Timeline`, `Scrubber`, `Player`) for visual
      frame-range selection — the actual differentiating feature
- [x] OCIO / LUT support for EXR export
- [x] Batch mode (multiple sources in one run)
- [x] Drag-and-drop file loading
- [x] Persistent shot queue for batch export from the GUI
- [x] Keyboard shortcuts (Space, ←/→, I/O)
- [x] CLI `--version` flag
- [x] Progress percentage in callbacks
- [x] Frame step clamping at boundaries
- [x] `ColorTransform.from_options()` shared validation (deduplicated
      color logic across CLI, batch, and GUI)
- [x] Python `logging` throughout CLI (replaced ad-hoc `print()`)
- [x] GitHub Actions CI config
- [x] Unit test coverage for `_lut_context`, `from_options`, `--version`

### Phase 2 — Feature Completion (all done)
- [x] LUT/OCIO on proxy (apply color transform to proxy output)
- [x] EXR compression options (none, rle, zip1, zip16)
- [x] Customizable frame padding (`%06d` → configurable)
- [x] Burn-in / watermark (frame number, timecode, source name on proxy)
- [x] Recent files menu (track recent clips in `~/.plate/recent.json`)
- [x] Undo for IN/OUT timeline selection
- [x] Configuration file (`~/.plate/config.toml` for defaults)
- [x] "Open containing folder" action after export

### Phase 3 — Road Ahead
- [ ] Thumbnail timeline (keyframe thumbnails on the ruler)
- [ ] EDL/CSV import of frame ranges
- [ ] Export presets ("ACES 2K", "Rec709 HD", "Archival 4K")
- [ ] Nuke script export (generate Nuke script pointing at EXR sequence)
- [ ] Watch folder / hot folder auto-processing
- [ ] Plug-in system for third-party export jobs
- [ ] Stereo 3D support (left/right eye handling)
