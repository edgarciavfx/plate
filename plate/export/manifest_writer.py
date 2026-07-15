"""ManifestWriter — writes the machine-readable manifest.json describing
a completed PlateSession.

This is the artifact that lets Plate's output plug into downstream
tooling (shot ingestion, automation, AI workflows) without anyone having
to re-derive metadata by hand.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..models.plate_session import PlateSession


class ManifestWriter:
    def __init__(self, session: PlateSession):
        self.session = session

    def build(self) -> dict:
        session = self.session
        metadata = session.metadata
        frame_range = session.frame_range

        manifest = {
            "shot": session.shot_name,
            "source": str(session.source_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "start_frame": frame_range.start_frame,
            "in": frame_range.in_frame,
            "out": frame_range.out_frame,
            "exported_frames": session.exported_frames,
            "proxy": str(session.proxy_path) if session.proxy_path else None,
            "exr_dir": str(session.exr_dir) if session.exr_dir else None,
        }

        if session.shot_mode:
            manifest["version"] = session.version
            manifest["versioned_name"] = session.versioned_name

        if metadata is not None:
            manifest.update(metadata.to_dict())

        ct = session.color_transform
        manifest["color_transform"] = ct.to_dict() if ct is not None else {"mode": None}

        manifest["comfy"] = None
        if session.comfy_dir is not None:
            cct = session.comfy_color_transform
            manifest["comfy"] = {
                "dir": str(session.comfy_dir),
                "pattern": session.comfy_pattern,
                "max_width": session.comfy_max_width,
                "frames": session.comfy_frames,
                "color_transform": cct.to_dict() if cct is not None else {"mode": None},
            }

        return manifest

    def write(self) -> Path:
        manifest_path = self.session.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(self.build(), indent=2))
        self.session.manifest_path = manifest_path
        return manifest_path
