# Screenshots

The README references two images from this folder. They're not committed yet —
capture them, save with the **exact filenames below**, and they'll render on both
GitHub and the PyPI project page (the README links to the `main`-branch raw URLs).

Launch the GUI with a real clip loaded before shooting:

```bash
pip install -e ".[gui]"
plate-gui
```

## `main_window.png`

Hero shot of the full application window.

- A clip loaded in the viewer showing a recognizable frame (not black/first-frame).
- Timeline populated with thumbnails, IN/OUT handles set to a visible sub-range.
- Transport controls visible.
- Shot queue panel with at least one queued shot, so the workflow reads at a glance.
- Window sized ~1600×1000 or larger; crop to the window (no desktop background).

Caption in README: *"Plate's GUI — load a clip, scrub through frames, set IN/OUT on the timeline, and export."*

## `timeline.png`

Tight crop of the timeline strip only.

- The timeline ruler with frame numbers.
- Both IN and OUT handles clearly visible with a highlighted selected range between them.
- The playhead/scrubber positioned mid-range.
- Crop to just the timeline widget (full width, ~150–250px tall).

Caption in README: *"The timeline ruler with IN/OUT handles and frame-accurate scrubbing."*

## Tips

- PNG, not JPG (crisp UI edges).
- Keep both under ~500 KB so the PyPI page and clone stay light.
- Use a consistent theme (the app's dark `style.qss`) across both shots.
