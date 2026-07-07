"""SVG icons for transport controls.

Each icon is an inline SVG string with a 16×16 viewBox.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


# -- icon definitions (16×16 viewBox) --------------------------------------

_PLAY = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<polygon points="4,2 14,8 4,14" fill="#e0e0e0"/>
</svg>"""

_PAUSE = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<rect x="3" y="2" width="4" height="12" rx="1" fill="#e0e0e0"/>
<rect x="9" y="2" width="4" height="12" rx="1" fill="#e0e0e0"/>
</svg>"""

_SKIP_BACK = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<polygon points="8,2 2,8 8,14" fill="#e0e0e0"/>
<polygon points="14,2 8,8 14,14" fill="#e0e0e0"/>
</svg>"""

_SKIP_FORWARD = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<polygon points="8,2 14,8 8,14" fill="#e0e0e0"/>
<polygon points="2,2 8,8 2,14" fill="#e0e0e0"/>
</svg>"""

_MARK_IN = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<rect x="2" y="2" width="2" height="12" rx="0.5" fill="#40916c"/>
<polygon points="6,8 12,3 12,13" fill="#40916c"/>
</svg>"""

_MARK_OUT = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<polygon points="4,3 4,13 10,8" fill="#d62828"/>
<rect x="12" y="2" width="2" height="12" rx="0.5" fill="#d62828"/>
</svg>"""

_LOOP = """<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
<path d="M2 8a6 6 0 0 1 10.5-4M14 8a6 6 0 0 1-10.5 4" fill="none" stroke="#e0e0e0" stroke-width="1.5" stroke-linecap="round"/>
<polygon points="12.5,1 15.5,4 12.5,7" fill="#e0e0e0"/>
<polygon points="3.5,9 0.5,12 3.5,15" fill="#e0e0e0"/>
</svg>"""


ICONS = {
    "play": _PLAY,
    "pause": _PAUSE,
    "skip_back": _SKIP_BACK,
    "skip_forward": _SKIP_FORWARD,
    "mark_in": _MARK_IN,
    "mark_out": _MARK_OUT,
    "loop": _LOOP,
}


def load_svg_icon(name: str, size: int = 16) -> QIcon:
    svg = ICONS.get(name)
    if svg is None:
        return QIcon()

    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
