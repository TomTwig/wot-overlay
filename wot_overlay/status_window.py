"""Small toast-style status window used to give feedback on hotkey actions."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StatusWindow(QWidget):
    """Temporary on-screen notification.

    Shows a short message at the top-center of the primary screen and fades
    itself out after ``duration_ms``.
    """

    def __init__(self, duration_ms: int, top_offset: int):
        super().__init__()
        self._duration = duration_ms
        self._top_offset = top_offset

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)

        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setStyleSheet(
            "color: white;"
            "background-color: rgba(0, 0, 0, 170);"
            "padding: 8px 16px;"
            "border-radius: 6px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    # ------------------------------------------------------------------

    def show_message(self, text: str) -> None:
        """Display ``text`` and auto-hide after the configured duration."""
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()

        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.center().x() - self.width() // 2
        y = screen.top() + self._top_offset
        self.move(x, y)

        self.show()
        self.raise_()
        self._timer.start(self._duration)
