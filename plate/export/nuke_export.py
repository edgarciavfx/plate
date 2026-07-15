from __future__ import annotations

from pathlib import Path

from ..models.plate_session import PlateSession


class NukeWriter:
    def __init__(self, session: PlateSession, frame_padding: int = 6):
        self.session = session
        self.frame_padding = frame_padding

    def build(self) -> str:
        session = self.session
        fr = session.frame_range
        metadata = session.metadata

        shot_name = session.frame_base_name
        padding = self.frame_padding
        pattern = f"{shot_name}.%0{padding}d.exr"
        exr_dir = session.exr_dir or session.plates_dir
        file_path = (exr_dir / pattern).as_posix()

        first = fr.in_frame
        last = fr.out_frame
        fps = metadata.fps if metadata else 24.0
        width = metadata.width if metadata else 1920
        height = metadata.height if metadata else 1080

        lines = []
        lines.append(f"Read {{")
        lines.append(f" inputs 0")
        lines.append(f" file {file_path}")
        lines.append(f" first {first}")
        lines.append(f" last {last}")
        lines.append(f" origfirst {first}")
        lines.append(f" origlast {last}")
        lines.append(f" name {shot_name}_reader")
        lines.append(f" selected true")
        lines.append(f" xpos 0")
        lines.append(f" ypos 0")
        lines.append(f"}}")

        lines.append("")
        lines.append(f"Viewer {{")
        lines.append(f" inputs 1")
        lines.append(f" name {shot_name}_viewer")
        lines.append(f" selected true")
        lines.append(f" xpos 0")
        lines.append(f" ypos {{+}}")
        lines.append(f"}}")

        lines.append("")

        ct = session.color_transform
        if ct is not None and ct.is_active():
            lines.append(f"# Color transform: {ct.to_dict()}")

        if session.comfy_dir is not None:
            lines.append(
                f"# ComfyUI PNGs: {(session.comfy_dir / (session.comfy_pattern or '')).as_posix()}"
                f" (max width {session.comfy_max_width})"
            )

        lines.append(f"# Source: {session.source_path}")
        lines.append(f"# Resolution: {width}x{height} @ {fps:.3f} fps")
        lines.append(f"# Frame range: {first}-{last} ({fr.frame_count} frames)")

        return "\n".join(lines) + "\n"

    def write(self) -> Path:
        nk_path = self.session.nuke_script_path
        nk_path.parent.mkdir(parents=True, exist_ok=True)
        nk_path.write_text(self.build())
        return nk_path
