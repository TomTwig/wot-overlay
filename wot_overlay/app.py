"""Main application / controller.

Wires together the overlay window, status toast, picker, file repository
and the global hotkey manager. This is the only module with real
orchestration logic — everything else is a small, self-contained component.

Selection flow
--------------
1. User holds the picker modifier key (default ``tab``) and taps a letter
   key (e.g. ``P``). The state machine opens a picker for that letter
   with the first entry highlighted.
2. While still holding the modifier, tapping the same letter again cycles
   through the list. Tapping a different letter switches to that letter's
   list.
3. When the modifier is released, the currently highlighted entry is
   applied and the picker is hidden. If no picker was open, releasing
   the modifier does nothing.
"""
from __future__ import annotations

import sys
import traceback
from typing import Optional

from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from . import config
from .hotkeys import HotkeyManager
from .overlay_window import OverlayWindow
from .picker_state import PickerState, PickerView
from .picker_window import PickerWindow
from .repository import OverlayEntry, OverlayRepository
from .status_window import StatusWindow


class OverlayController(QObject):
    """Routes hotkey events to the Qt GUI thread and performs the actions.

    Hotkey callbacks run on the `keyboard` library's background thread. They
    emit ``_do_action`` which — because the signal is queued — wakes the Qt
    event loop and runs ``_handle_action`` on the GUI thread.
    """

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
        self.picker = PickerWindow()
        self.picker_state = PickerState(self.repo)

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
        self.status.show_message(
            f"WoT overlay ready  —  tap {config.HOTKEY_TOGGLE.upper()} to toggle"
        )

    def _load_overlays(self) -> None:
        try:
            self.repo.scan()
        except FileNotFoundError:
            config.OVERLAYS_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[wot-overlay] Created empty overlays folder at: {config.OVERLAYS_DIR}")
            print("[wot-overlay] Drop <mapname>_<variant>.png files in and restart.")
            return

        print("[wot-overlay] Overlays folder:", config.OVERLAYS_DIR)
        print("[wot-overlay] Loaded overlays:")
        print(self.repo.describe())

        if self.repo.ignored:
            print("\n[wot-overlay] Ignored files (bad filename):")
            for p in self.repo.ignored:
                print(f"  {p.name}")

    # ==================================================================
    # Hotkey registration
    # ==================================================================

    def _register_hotkeys(self) -> None:
        modifier = config.PICKER_MODIFIER.lower()

        # Collect reserved chord strings so a letter hotkey never stomps
        # on a globally configured action (e.g. if someone sets both
        # PICKER_MODIFIER = "alt" and HOTKEY_CLEAR = "alt+0", the letter
        # "0" would collide — "0" isn't a letter, so fine, but this check
        # catches general collisions too).
        reserved = {
            config.HOTKEY_CLEAR.lower(),
            config.HOTKEY_OPACITY_UP.lower(),
            config.HOTKEY_OPACITY_DOWN.lower(),
            config.HOTKEY_QUIT.lower(),
        }
        if "+" in config.HOTKEY_TOGGLE:
            reserved.add(config.HOTKEY_TOGGLE.lower())

        for letter in self.repo.letters():
            hk = f"{modifier}+{letter}"
            if hk in reserved:
                print(
                    f"[wot-overlay] Skipping letter hotkey {hk!r} — reserved "
                    "for a global action. Either rename the map or change "
                    "the conflicting hotkey in config.json."
                )
                continue
            self._safe_register(hk, self._make_letter_cb(letter))

        # Overlay toggle: tap a single key, or register as a normal chord
        # if the user configured one.
        if "+" in config.HOTKEY_TOGGLE:
            self._safe_register(config.HOTKEY_TOGGLE, lambda: self._emit("toggle"))
        else:
            try:
                self.hotkeys.watch_tap(
                    config.HOTKEY_TOGGLE,
                    lambda: self._emit("toggle"),
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[wot-overlay] Failed to register tap hotkey "
                    f"{config.HOTKEY_TOGGLE!r}: {exc}"
                )

        # Other global controls
        self._safe_register(config.HOTKEY_CLEAR,        lambda: self._emit("clear"))
        self._safe_register(config.HOTKEY_OPACITY_UP,   lambda: self._emit("opacity_up"))
        self._safe_register(config.HOTKEY_OPACITY_DOWN, lambda: self._emit("opacity_down"))
        self._safe_register(config.HOTKEY_QUIT,         lambda: self._emit("quit"))

        # Releasing the picker modifier confirms the current selection.
        try:
            self.hotkeys.register_release(
                modifier,
                lambda: self._emit("picker_released"),
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[wot-overlay] Failed to register release hook for "
                f"{modifier!r}: {exc}"
            )

    def _safe_register(self, hotkey: str, cb) -> None:
        try:
            self.hotkeys.register(hotkey, cb)
        except Exception as exc:  # noqa: BLE001
            print(f"[wot-overlay] Failed to register hotkey {hotkey!r}: {exc}")

    def _make_letter_cb(self, letter: str):
        # Default-arg trick binds ``letter`` at definition time.
        def _cb(_letter=letter):
            self._emit("letter", _letter)
        return _cb

    def _emit(self, action: str, payload: object = None) -> None:
        self._do_action.emit(action, payload)

    # ==================================================================
    # Actions (Qt thread)
    # ==================================================================

    def _handle_action(self, action: str, payload: object) -> None:
        try:
            if action == "letter":
                self._action_letter(str(payload))
            elif action == "picker_released":
                self._action_picker_released()
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
            traceback.print_exc()

    # -- picker --------------------------------------------------------

    def _action_letter(self, letter: str) -> None:
        view: Optional[PickerView] = self.picker_state.press_letter(letter)
        if view is None:
            self.status.show_message(f"No overlays for {letter.upper()}")
            return
        self.picker.show_picker(
            config.PICKER_MODIFIER,
            view.letter,
            view.entries,
            view.selected_index,
        )

    def _action_picker_released(self) -> None:
        # Fires on every picker-modifier key-up. Only act if a picker was open.
        entry: Optional[OverlayEntry] = self.picker_state.release()
        self.picker.hide()
        if entry is None:
            return
        self._apply_entry(entry)

    def _apply_entry(self, entry: OverlayEntry) -> None:
        if not entry.path.exists():
            self.status.show_message(f"Missing file: {entry.path.name}")
            return
        if not self.overlay.load_image(entry.path):
            self.status.show_message(f"Invalid image: {entry.path.name}")
            return

        if not self._visible:
            self._visible = True
            self.overlay.show()

        self.status.show_message(f"Loaded: {entry.label}")

    # -- global actions ------------------------------------------------

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
        # Drop any in-progress picker so the release hook doesn't fire a
        # stale selection during the shutdown delay.
        self.picker_state.reset()
        self.picker.hide()
        self.status.show_message("Bye!")
        QTimer.singleShot(300, self.app.quit)

    # ==================================================================

    def shutdown(self) -> None:
        self.hotkeys.clear()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    controller = OverlayController(app)
    controller.start()
    try:
        return app.exec()
    finally:
        controller.shutdown()
