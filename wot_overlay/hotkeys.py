"""Thin wrapper around the `keyboard` library.

Why `keyboard`?
    - Supports global hotkeys on Windows without admin rights.
    - Understands chord syntax like ``alt+p`` natively.
    - Can hook raw key-release events via ``on_release_key``, which is how
      the picker confirms the selection once Alt is released.

Threading note
--------------
The `keyboard` library fires callbacks on a background thread. Touching Qt
widgets from that thread is unsafe, so callbacks here must only emit a
thread-safe signal; the controller (``app.OverlayController``) marshals the
work to the GUI thread.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

import keyboard


class HotkeyManager:
    def __init__(self) -> None:
        self._press_handles: List[object] = []
        self._release_handles: List[Tuple[str, object]] = []

    # ------------------------------------------------------------------

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """Register ``callback`` for a press-down combo like ``alt+p``."""
        handle = keyboard.add_hotkey(
            hotkey,
            callback,
            suppress=False,
            trigger_on_release=False,
        )
        self._press_handles.append(handle)

    def register_release(self, key: str, callback: Callable[[], None]) -> None:
        """Register ``callback`` to fire when ``key`` is released.

        Unlike ``register`` this is a plain key hook, not a chord — it fires
        every time the user lets go of that key, regardless of modifier
        state. The caller is responsible for filtering out releases that
        are not interesting (we do that via explicit state in the app).
        """
        handle = keyboard.on_release_key(
            key,
            lambda _event: callback(),
            suppress=False,
        )
        self._release_handles.append((key, handle))

    # ------------------------------------------------------------------

    def clear(self) -> None:
        for h in self._press_handles:
            try:
                keyboard.remove_hotkey(h)
            except (KeyError, ValueError):
                pass
        self._press_handles.clear()

        for _key, h in self._release_handles:
            try:
                keyboard.unhook(h)
            except (KeyError, ValueError):
                pass
        self._release_handles.clear()
