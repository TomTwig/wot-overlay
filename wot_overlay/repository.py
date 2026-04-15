"""Scans the overlays folder and groups entries by first letter.

Naming convention
-----------------
Files must be named ``<mapname>_<variant>.png`` where:
    - ``mapname``  : ASCII letters/digits, starts with a letter
    - ``variant``  : positive integer

Grouping
--------
Entries are sorted alphabetically by ``mapname`` and then by ``variant``
ascending. They are then grouped by the first letter of ``mapname``. This is
what the picker uses: pressing ``Alt + <letter>`` shows the list for that
letter, pressing it again cycles through that list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# <mapname>_<variant>.png  — mapname must start with an ASCII letter.
_FILENAME_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9]*)_(?P<variant>\d+)\.png$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OverlayEntry:
    """A single overlay file reachable via the picker."""
    map_name: str      # normalised lower-case, e.g. "prokhorovka"
    variant: int       # e.g. 2
    path: Path

    @property
    def letter(self) -> str:
        return self.map_name[0]

    @property
    def label(self) -> str:
        """Human-readable label shown in the picker and status toasts."""
        return f"{self.map_name.capitalize()} {self.variant}"


class OverlayRepository:
    """Scans a directory and exposes entries grouped by first letter."""

    def __init__(self, folder: Path):
        self.folder: Path = folder
        self.by_letter: Dict[str, List[OverlayEntry]] = {}
        self.ignored: List[Path] = []

    # ------------------------------------------------------------------

    def scan(self) -> None:
        """(Re)populate ``self.by_letter`` from disk.

        Raises:
            FileNotFoundError: if the folder does not exist.
        """
        self.by_letter.clear()
        self.ignored.clear()

        if not self.folder.exists():
            raise FileNotFoundError(f"Overlays folder not found: {self.folder}")

        png_files = sorted(self.folder.glob("*.png"))

        parsed: List[OverlayEntry] = []
        for p in png_files:
            m = _FILENAME_RE.match(p.name)
            if not m:
                self.ignored.append(p)
                continue
            parsed.append(
                OverlayEntry(
                    map_name=m.group("name").lower(),
                    variant=int(m.group("variant")),
                    path=p,
                )
            )

        # Stable sort: map name, then variant.
        parsed.sort(key=lambda e: (e.map_name, e.variant))

        for entry in parsed:
            self.by_letter.setdefault(entry.letter, []).append(entry)

    # ------------------------------------------------------------------

    def letters(self) -> List[str]:
        """Sorted list of all letters that have at least one overlay."""
        return sorted(self.by_letter.keys())

    def entries_for_letter(self, letter: str) -> List[OverlayEntry]:
        return list(self.by_letter.get(letter.lower(), []))

    def describe(self) -> str:
        """Multi-line human-readable listing, used for startup logging."""
        if not self.by_letter:
            return "  (no overlays found)"
        lines: List[str] = []
        for letter in sorted(self.by_letter.keys()):
            lines.append(f"  Alt+{letter.upper()}:")
            for e in self.by_letter[letter]:
                lines.append(f"      {e.label:<24}  ({e.path.name})")
        return "\n".join(lines)
