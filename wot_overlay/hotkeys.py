"""Thin wrapper around the `keyboard` library.

Why `keyboard`?
    - Supports global hotkeys on Windows without admin rights.
    - Understands chord syntax like ``alt+p+1`` natively, which is exactly
      the selection pattern the user wants.

Threading note
--------------
The `keyboard` library fires callbacks on a background thread. Touching Qt
widgets from that thread is unsafe, so callbacks here must only emit a
thread-safe signal; the controller (``app.OverlayController``) marshals the
work to the GUI thread.
"""
from __future__ import annotations

from typing import Callable, List

import keyboard


class HotkeyManager:
    def __init__(self) -> None:
        self._handles: List[object] = []

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """Register ``callback`` for ``hotkey``.

        Raises:
            ValueError: if the hotkey string is not understood by the
                underlying library.
        """
        handle = keyboard.add_hotkey(
            hotkey,
            callback,
            suppress=False,           # don't swallow keys from the game
            trigger_on_release=False,
        )
        self._handles.append(handle)

    def clear(self) -> None:
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except (KeyError, ValueError):
                pass
        self._handles.clear()
