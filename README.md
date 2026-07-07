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
```

### Example

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
| `--in`              | required        | IN frame number (inclusive)                        |
| `--out`             | required        | OUT frame number (inclusive)                       |
| `--start-frame`     | `0`             | First frame number embedded in the source file     |
| `--output`          | `./output`      | Root output directory                              |
| `--proxy-width`     | `1920`          | Max proxy width (never scales up)                  |
| `--exr-pixfmt`      | `gbrpf32le`     | EXR pixel format (32-bit float linear)              |
| `--skip-exr`        | off             | Skip EXR sequence generation                        |
| `--skip-proxy`      | off             | Skip proxy generation                                |

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

- [x] `ffprobe` wrapper -> `VideoMetadata`
- [x] `ffmpeg` wrappers -> EXR sequence + proxy
- [x] `PlatePipeline` orchestration + manifest
- [x] CLI
- [x] PySide6 viewer (`Timeline`, `Scrubber`, `Player`) for visual
      frame-range selection — the actual differentiating feature
- [ ] OCIO / LUT support for EXR export
- [ ] Batch mode (multiple sources in one run)
- [ ] Drag-and-drop file loading
- [ ] Persistent shot queue for batch export from the GUI
