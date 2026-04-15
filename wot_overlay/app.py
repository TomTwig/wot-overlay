"""Main application / controller.

Wires together the overlay window, status toast, file repository and the
global hotkey manager. This is the only module with real orchestration
logic — everything else is a small, self-contained component.
"""
from __future__ import annotations

import sys
import traceback
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QApplication

from . import config
from .hotkeys import HotkeyManager
from .overlay_window import OverlayWindow
from .repository import OverlayEntry, OverlayRepository
from .status_window import StatusWindow


class OverlayController(QObject):
    """Routes hotkey events to the Qt GUI thread and performs the actions.

    Hotkey callbacks run on the `keyboard` library's background thread. They
    emit ``_do_action`` which — because the signal is queued — wakes the Qt
    event loop and runs ``_handle_action`` on the GUI thread.
    """

    # (action name, optional payload) — payload is ``object`` to keep it loose
    _do_action = Signal(str, object)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.repo = OverlayRepository(config.OVERLAYS_DIR)

        self.overlay = OverlayWindow(
            size=config.OVERLAY_SIZE,
            offset_right=config.OFFSET_RIGHT,
            offset_bottom=config.OFFSET_BOTTOM,
            opacity=config.DEFAULT_OPACITY,
        )
        self.status = StatusWindow(
            duration_ms=config.STATUS_DURATION_MS,
            top_offset=config.STATUS_OFFSET_TOP,
        )
        self.hotkeys = HotkeyManager()

        self._visible = not config.START_HIDDEN
        self._do_action.connect(self._handle_action, Qt.QueuedConnection)

    # ==================================================================
    # Startup
    # ==================================================================

    def start(self) -> None:
        self._load_overlays()
        self._register_hotkeys()
        if self._visible:
            self.overlay.show()
        self.status.show_message("WoT overlay ready  —  Alt+O to toggle")

    def _load_overlays(self) -> None:
        try:
            self.repo.scan()
        except FileNotFoundError:
            # Graceful recovery: create the folder and keep running.
            config.OVERLAYS_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[wot-overlay] Created empty overlays folder at: {config.OVERLAYS_DIR}")
            print("[wot-overlay] Drop <mapname>_<variant>.png files in and restart.")
            return

        print("[wot-overlay] Overlays folder:", config.OVERLAYS_DIR)
        print("[wot-overlay] Loaded overlays:")
        print(self.repo.describe())

        if self.repo.ignored:
            print("\n[wot-overlay] Ignored files (bad name or >9 per letter group):")
            for p in self.repo.ignored:
                print(f"  {p.name}")

    # ==================================================================
    # Hotkey registration
    # ==================================================================

    def _register_hotkeys(self) -> None:
        # Per-overlay selection chords: alt + <letter> + <slot>
        for (letter, slot) in self.repo.entries.keys():
            self._safe_register(
                f"alt+{letter}+{slot}",
                self._make_select_cb(letter, slot),
            )

        # Global controls
        self._safe_register(config.HOTKEY_TOGGLE,       lambda: self._emit("toggle"))
        self._safe_register(config.HOTKEY_CLEAR,        lambda: self._emit("clear"))
        self._safe_register(config.HOTKEY_OPACITY_UP,   lambda: self._emit("opacity_up"))
        self._safe_register(config.HOTKEY_OPACITY_DOWN, lambda: self._emit("opacity_down"))
        self._safe_register(config.HOTKEY_QUIT,         lambda: self._emit("quit"))

    def _safe_register(self, hotkey: str, cb) -> None:
        try:
            self.hotkeys.register(hotkey, cb)
        except Exception as exc:  # noqa: BLE001 — keyboard lib can raise a lot
            print(f"[wot-overlay] Failed to register hotkey {hotkey!r}: {exc}")

    def _make_select_cb(self, letter: str, slot: int):
        # Closure capture with default args keeps letter/slot bound correctly.
        def _cb(_letter=letter, _slot=slot):
            self._emit("select", (_letter, _slot))
        return _cb

    def _emit(self, action: str, payload: object = None) -> None:
        """Marshal an action from the keyboard thread to the Qt thread."""
        self._do_action.emit(action, payload)

    # ==================================================================
    # Actions (Qt thread)
    # ==================================================================

    def _handle_action(self, action: str, payload: object) -> None:
        try:
            if action == "select":
                letter, slot = payload  # type: ignore[misc]
                self._action_select(letter, slot)
            elif action == "toggle":
                self._action_toggle()
            elif action == "clear":
                self._action_clear()
            elif action == "opacity_up":
                self._action_opacity(+config.OPACITY_STEP)
            elif action == "opacity_down":
                self._action_opacity(-config.OPACITY_STEP)
            elif action == "quit":
                self._action_quit()
        except Exception:
            # Never let a handler kill the event loop — just log it.
            traceback.print_exc()

    def _action_select(self, letter: str, slot: int) -> None:
        entry: Optional[OverlayEntry] = self.repo.get(letter, slot)
        if entry is None:
            self.status.show_message(f"No overlay for Alt+{letter.upper()}+{slot}")
            return
        if not entry.path.exists():
            self.status.show_message(f"Missing file: {entry.path.name}")
            return
        if not self.overlay.load_image(entry.path):
            self.status.show_message(f"Invalid image: {entry.path.name}")
            return

        # Selecting an overlay implicitly shows the window.
        if not self._visible:
            self._visible = True
            self.overlay.show()

        self.status.show_message(f"Loaded: {entry.label}")

    def _action_toggle(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self.overlay.show()
            self.status.show_message("Overlay on")
        else:
            self.overlay.hide()
            self.status.show_message("Overlay off")

    def _action_clear(self) -> None:
        self.overlay.clear_image()
        self.status.show_message("Overlay cleared")

    def _action_opacity(self, delta: float) -> None:
        new_val = round(self.overlay.opacity + delta, 2)
        new_val = max(config.MIN_OPACITY, min(config.MAX_OPACITY, new_val))
        self.overlay.set_opacity(new_val)
        self.status.show_message(f"Opacity: {int(new_val * 100)}%")

    def _action_quit(self) -> None:
        self.status.show_message("Bye!")
        # Let the toast render briefly, then cleanly tear down the app.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self.app.quit)

    # ==================================================================

    def shutdown(self) -> None:
        self.hotkeys.clear()


def main() -> int:
    app = QApplication(sys.argv)
    # Overlay / status windows are Qt.Tool and may be hidden; keep the app
    # alive until the user closes it from the console.
    app.setQuitOnLastWindowClosed(False)

    controller = OverlayController(app)
    controller.start()
    try:
        return app.exec()
    finally:
        controller.shutdown()
