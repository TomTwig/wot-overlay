"""Pure state machine for the overlay picker.

Kept separate from Qt so it can be unit-tested without a display.

Usage
-----
Create a ``PickerState`` with a ``repo`` (anything exposing
``entries_for_letter(letter)``). Drive it with:

- ``press_letter(letter)`` when the user presses ``Alt+<letter>``
- ``release()`` when the user releases Alt
- ``reset()`` to discard any in-progress picker without applying

After ``press_letter`` the state machine either opens a new picker or cycles
the current one and returns the data that should be drawn on screen. After
``release`` it returns the entry that should be applied, or ``None`` if the
user never started a picker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from .repository import OverlayEntry


class _RepoLike(Protocol):
    def entries_for_letter(self, letter: str) -> List[OverlayEntry]: ...


@dataclass
class PickerView:
    """What the picker UI should currently display."""
    letter: str
    entries: List[OverlayEntry]
    selected_index: int


class PickerState:
    def __init__(self, repo: _RepoLike):
        self._repo = repo
        self._letter: Optional[str] = None
        self._entries: List[OverlayEntry] = []
        self._index: int = 0

    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._letter is not None

    @property
    def current_entry(self) -> Optional[OverlayEntry]:
        if not self.is_open or not self._entries:
            return None
        return self._entries[self._index]

    # ------------------------------------------------------------------

    def press_letter(self, letter: str) -> Optional[PickerView]:
        """Handle ``Alt+<letter>``. Returns the view to render, or ``None``
        if there are no overlays for that letter."""
        letter = letter.lower()

        if self._letter == letter and self._entries:
            # Cycle to next entry, wrap around.
            self._index = (self._index + 1) % len(self._entries)
            return PickerView(self._letter, list(self._entries), self._index)

        # Either no picker open yet, or switching to a different letter.
        entries = self._repo.entries_for_letter(letter)
        if not entries:
            return None

        self._letter = letter
        self._entries = entries
        self._index = 0
        return PickerView(self._letter, list(self._entries), self._index)

    def release(self) -> Optional[OverlayEntry]:
        """Handle Alt key-up. Returns the entry the user picked, or
        ``None`` if no picker was open."""
        entry = self.current_entry
        self._letter = None
        self._entries = []
        self._index = 0
        return entry

    def reset(self) -> None:
        """Discard any in-progress picker without applying it."""
        self._letter = None
        self._entries = []
        self._index = 0
