"""Transient picker shown while Alt is held.

Displays the list of overlays for the currently pressed letter and
highlights the one that will be applied when Alt is released.
"""
from __future__ import annotations

from html import escape
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .repository import OverlayEntry


class PickerWindow(QWidget):
    """Small, centered, click-through list widget.

    The window is always-on-top and ``WA_TranslucentBackground`` so only the
    rounded dark panel is visible. Content is rendered as rich text so the
    currently selected row can be highlighted without a second widget.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._label = QLabel("", self)
        self._label.setTextFormat(Qt.RichText)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setStyleSheet(
            "color: white;"
            "background-color: rgba(0, 0, 0, 190);"
            "padding: 12px 18px;"
            "border-radius: 8px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._label)

    # ------------------------------------------------------------------

    def show_picker(
        self,
        modifier: str,
        letter: str,
        entries: List[OverlayEntry],
        selected_index: int,
    ) -> None:
        """Render the list for ``letter`` with ``selected_index`` highlighted."""
        if not entries:
            self.hide()
            return

        header = f"<b>{escape(modifier.upper())} + {escape(letter.upper())}</b>"
        rows: List[str] = [header, ""]
        for i, entry in enumerate(entries):
            label = escape(entry.label)
            if i == selected_index:
                rows.append(
                    f"<span style='color:#ffd44a;'>&#9654;&nbsp;{label}</span>"
                )
            else:
                rows.append(f"&nbsp;&nbsp;&nbsp;{label}")

        self._label.setText("<br>".join(rows))
        self._label.adjustSize()
        self.adjustSize()

        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.center().x() - self.width() // 2
        y = screen.center().y() - self.height() // 2
        self.move(x, y)

        self.show()
        self.raise_()
