from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_CONFIG_DIR = Path.home() / ".plate"
_RECENT_PATH = _CONFIG_DIR / "recent.json"

_MAX_ENTRIES = 10


class RecentFiles:
    def __init__(self, entries: Optional[list[dict]] = None):
        self.entries: list[dict] = entries if entries is not None else []

    @property
    def paths(self) -> list[str]:
        return [e["path"] for e in self.entries]

    @classmethod
    def load(cls) -> RecentFiles:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not _RECENT_PATH.exists():
            return cls()
        try:
            raw = json.loads(_RECENT_PATH.read_text())
            if not isinstance(raw, list):
                return cls()
            entries = [
                e for e in raw
                if isinstance(e, dict) and "path" in e
            ][:_MAX_ENTRIES]
            return cls(entries)
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        raw = [
            {"path": e["path"], "timestamp": e.get("timestamp", "")}
            for e in self.entries
        ]
        _RECENT_PATH.write_text(json.dumps(raw, indent=2))

    def record(self, path: str) -> None:
        self.entries = [
            e for e in self.entries if e["path"] != path
        ]
        self.entries.insert(0, {
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.entries = self.entries[:_MAX_ENTRIES]
        self.save()
