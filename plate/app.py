"""GUI entry point.

    python -m plate.app

Launches the PySide6 viewer. The GUI only configures + drives a
PlatePipeline via SessionController — it contains no ffmpeg/ffprobe
logic itself.
"""

from __future__ import annotations

import sys


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
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
