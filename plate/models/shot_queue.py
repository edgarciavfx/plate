from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


_QUEUE_DIR = Path.home() / ".plate"
_QUEUE_PATH = _QUEUE_DIR / "queue.json"


@dataclass
class QueueEntry:
    source: str
    in_frame: int
    out_frame: int
    start_frame: int = 0
    output_root: str = "./output"
    proxy_max_width: int = 1920
    exr_pixel_format: str = "gbrpf32le"
    exr_compression: str = "zip1"
    frame_padding: int = 6
    skip_exr: bool = False
    skip_proxy: bool = False
    export_nuke_script: bool = False
    color_mode: str = "none"
    lut_path: Optional[str] = None
    ocio_config: Optional[str] = None
    ocio_src: Optional[str] = None
    ocio_dst: Optional[str] = None
    burn_in: Optional[list[str]] = None
    status: str = "pending"
    error: Optional[str] = None
    manifest_path: Optional[str] = None

    def is_pending(self) -> bool:
        return self.status == "pending"


class ShotQueue:
    def __init__(self, entries: Optional[list[QueueEntry]] = None):
        self.entries = entries if entries is not None else []

    @classmethod
    def load(cls) -> ShotQueue:
        _QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        if not _QUEUE_PATH.exists():
            return cls()
        try:
            raw = json.loads(_QUEUE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        entries = [QueueEntry(**item) for item in raw]
        for e in entries:
            if e.status == "processing":
                e.status = "pending"
                e.error = None
        return cls(entries)

    def save(self) -> None:
        _QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        raw = [asdict(e) for e in self.entries]
        _QUEUE_PATH.write_text(json.dumps(raw, indent=2))

    def add(self, entry: QueueEntry) -> None:
        self.entries.append(entry)
        self.save()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.entries):
            del self.entries[index]
            self.save()

    def move_up(self, index: int) -> None:
        if index > 0:
            self.entries[index], self.entries[index - 1] = self.entries[index - 1], self.entries[index]
            self.save()

    def move_down(self, index: int) -> None:
        if index < len(self.entries) - 1:
            self.entries[index], self.entries[index + 1] = self.entries[index + 1], self.entries[index]
            self.save()

    def clear_completed(self) -> None:
        self.entries = [e for e in self.entries if e.status not in ("done", "failed")]
        self.save()

    def clear_all(self) -> None:
        self.entries.clear()
        self.save()

    def pending_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.is_pending()]

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> QueueEntry:
        return self.entries[index]
