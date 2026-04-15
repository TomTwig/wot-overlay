"""Thin wrapper around the `keyboard` library.

Provides three primitives:

- ``register(chord, cb)``  — chord press events via ``keyboard.add_hotkey``
- ``register_release(key, cb)``  — key-up events via ``on_release_key``
- ``watch_tap(key, cb)`` — *tap* events: the key was pressed and released
  without any other key pressed in between. Used to turn a modifier key
  like Alt into a clean toggle without stealing it from chords such as
  ``alt+shift+q``.

Threading note
--------------
The `keyboard` library fires callbacks on a background thread. Touching Qt
widgets from that thread is unsafe, so callbacks here must only emit a
thread-safe signal; the controller (``app.OverlayController``) marshals the
work to the GUI thread.
"""
from __future__ import annotations

import traceback
from typing import Callable, Dict, List, Optional, Tuple

import keyboard


class KeyTapDetector:
    """Detects *clean taps* of watched keys.

    A "clean tap" is a press-then-release of a watched key with no other
    key pressed in between. This lets us treat a modifier like Alt as a
    toggle while keeping it usable as part of chords like ``alt+shift+q``.
    """

    def __init__(self) -> None:
        self._watched: Dict[str, Callable[[], None]] = {}
        self._clean: Dict[str, bool] = {}
        self._hook: Optional[object] = None

    # ------------------------------------------------------------------

    def watch(self, key: str, callback: Callable[[], None]) -> None:
        key = key.lower()
        self._watched[key] = callback
        self._clean[key] = False

    def start(self) -> None:
        if self._hook is None and self._watched:
            self._hook = keyboard.hook(self._on_event)

    def stop(self) -> None:
        if self._hook is not None:
            try:
                keyboard.unhook(self._hook)
            except (KeyError, ValueError):
                pass
            self._hook = None

    # ------------------------------------------------------------------

    def process_event(self, name: str, event_type: str) -> None:
        """Pure event processor, extracted so it can be unit-tested."""
        name = (name or "").lower()

        if event_type == "down":
            if name in self._watched:
                # Fresh press of a watched key starts a new tap candidate
                # and invalidates any previously pending ones.
                for key in self._clean:
                    self._clean[key] = (key == name)
            else:
                # Any foreign key press invalidates every pending tap.
                for key in self._clean:
                    self._clean[key] = False

        elif event_type == "up":
            if name in self._watched and self._clean.get(name, False):
                self._clean[name] = False
                try:
                    self._watched[name]()
                except Exception:
                    traceback.print_exc()
            elif name in self._clean:
                self._clean[name] = False

    def _on_event(self, event) -> None:
        self.process_event(
            getattr(event, "name", "") or "",
            getattr(event, "event_type", "") or "",
        )


class HotkeyManager:
    def __init__(self) -> None:
        self._press_handles: List[object] = []
        self._release_handles: List[Tuple[str, object]] = []
        self._tap_detector = KeyTapDetector()

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
        """Register ``callback`` to fire when ``key`` is released."""
        handle = keyboard.on_release_key(
            key,
            lambda _event: callback(),
            suppress=False,
        )
        self._release_handles.append((key, handle))

    def watch_tap(self, key: str, callback: Callable[[], None]) -> None:
        """Register ``callback`` to fire on a clean tap of ``key``."""
        self._tap_detector.watch(key, callback)
        self._tap_detector.start()

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

        self._tap_detector.stop()
