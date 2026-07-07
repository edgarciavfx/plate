"""GUI entry point.

    python -m plate.app

Launches the PySide6 viewer. The GUI only configures + drives a
PlatePipeline via SessionController — it contains no ffmpeg/ffprobe
logic itself.
"""

from __future__ import annotations

import sys
from importlib.resources import files


def _apply_style(app) -> None:
    app.setStyle("Fusion")
    try:
        qss = (files("plate.ui") / "style.qss").read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except (FileNotFoundError, OSError):
        pass


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is required for the GUI. Install it with:\n"
            "  pip install PySide6",
            file=sys.stderr,
        )
        return 1

    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    _apply_style(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
