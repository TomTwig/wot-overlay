"""The transparent always-on-top overlay window."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class OverlayWindow(QWidget):
    """Frameless, translucent, click-through, always-on-top PNG viewer.

    The window uses ``Qt.WindowTransparentForInput`` so mouse events pass
    straight through to the game underneath — on Windows this maps to
    ``WS_EX_TRANSPARENT`` and is the clean way to get click-through.
    """

    def __init__(
        self,
        size: int,
        offset_right: int,
        offset_bottom: int,
        opacity: float,
    ):
        super().__init__()
        self._size = size
        self._offset_right = offset_right
        self._offset_bottom = offset_bottom
        self._opacity = opacity
        self._current_path: Optional[Path] = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool                        # keeps it out of the taskbar
            | Qt.WindowTransparentForInput   # click-through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.label)

        self.resize(size, size)
        self._reposition()
        self.setWindowOpacity(opacity)

    # ------------------------------------------------------------------

    def _reposition(self) -> None:
        """Snap to the bottom-right of the primary screen with offsets."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self._size - self._offset_right + 1
        y = screen.bottom() - self._size - self._offset_bottom + 1
        self.move(x, y)

    # ------------------------------------------------------------------

    def load_image(self, path: Path) -> bool:
        """Load and display a PNG file. Returns False on failure."""
        pm = QPixmap(str(path))
        if pm.isNull():
            return False
        scaled = pm.scaled(
            self._size,
            self._size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.label.setPixmap(scaled)
        self._current_path = path
        return True

    def clear_image(self) -> None:
        self.label.clear()
        self._current_path = None

    # ------------------------------------------------------------------

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(1.0, value))
        self.setWindowOpacity(self._opacity)

    @property
    def opacity(self) -> float:
        return self._opacity

    @property
    def current_path(self) -> Optional[Path]:
        return self._current_path
