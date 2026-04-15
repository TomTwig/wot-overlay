"""Scans the overlays folder and builds a deterministic hotkey mapping.

Naming convention
-----------------
Files must be named ``<mapname>_<variant>.png`` where:
    - ``mapname``  : letters/digits, starts with a letter
    - ``variant``  : positive integer

Mapping rules
-------------
1. Only files matching the convention are considered; the rest are ignored
   (and reported once at startup).
2. Valid files are sorted alphabetically by ``mapname`` and then by
   ``variant`` ascending. This gives a stable, predictable order.
3. Files are grouped by the first letter of ``mapname``.
4. Inside a group, each file gets a running slot number 1..9. This means
   every variant is addressable (including ``prokhorovka_2``), and the
   hotkey is always ``Alt + <letter> + <slot>``.
5. If a group has more than 9 files, the surplus is ignored in the MVP:
   we do not have a sensible single-digit hotkey for them. A warning is
   logged on startup.

Example for folder containing::

    paris_1.png
    pilsen_1.png
    prokhorovka_1.png
    prokhorovka_2.png

gives::

    Alt + P + 1  -> paris_1.png
    Alt + P + 2  -> pilsen_1.png
    Alt + P + 3  -> prokhorovka_1.png
    Alt + P + 4  -> prokhorovka_2.png
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# <mapname>_<variant>.png  — mapname must start with a letter.
_FILENAME_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9]*)_(?P<variant>\d+)\.png$",
    re.IGNORECASE,
)

MAX_SLOTS_PER_GROUP = 9


@dataclass(frozen=True)
class OverlayEntry:
    """A single overlay file that is reachable via a hotkey."""
    map_name: str      # normalised lower-case, e.g. "prokhorovka"
    variant: int       # e.g. 2
    path: Path
    letter: str        # first letter, lower-case
    slot: int          # 1..9 inside its letter group

    @property
    def label(self) -> str:
        """Human-readable label used in status messages."""
        return f"{self.map_name.capitalize()} {self.variant}"

    @property
    def hotkey(self) -> str:
        return f"alt+{self.letter}+{self.slot}"


class OverlayRepository:
    """Scans a directory and exposes a (letter, slot) -> OverlayEntry map."""

    def __init__(self, folder: Path):
        self.folder: Path = folder
        self.entries: Dict[Tuple[str, int], OverlayEntry] = {}
        self.ignored: List[Path] = []

    # ------------------------------------------------------------------

    def scan(self) -> None:
        """(Re)populate ``self.entries`` from disk.

        Raises:
            FileNotFoundError: if the folder does not exist.
        """
        self.entries.clear()
        self.ignored.clear()

        if not self.folder.exists():
            raise FileNotFoundError(f"Overlays folder not found: {self.folder}")

        # Deterministic order: sorted() gives alphabetical by filename.
        png_files = sorted(self.folder.glob("*.png"))

        parsed: List[Tuple[str, int, Path]] = []
        for p in png_files:
            m = _FILENAME_RE.match(p.name)
            if not m:
                self.ignored.append(p)
                continue
            parsed.append((m.group("name").lower(), int(m.group("variant")), p))

        # Primary sort: map name, secondary: variant number.
        parsed.sort(key=lambda t: (t[0], t[1]))

        # Assign a running slot number inside each letter group.
        slot_counter: Dict[str, int] = {}
        for name, variant, path in parsed:
            letter = name[0]
            slot_counter[letter] = slot_counter.get(letter, 0) + 1
            slot = slot_counter[letter]
            if slot > MAX_SLOTS_PER_GROUP:
                # No single-digit hotkey available for this one.
                self.ignored.append(path)
                continue
            self.entries[(letter, slot)] = OverlayEntry(
                map_name=name,
                variant=variant,
                path=path,
                letter=letter,
                slot=slot,
            )

    # ------------------------------------------------------------------

    def get(self, letter: str, slot: int) -> Optional[OverlayEntry]:
        return self.entries.get((letter.lower(), slot))

    def describe(self) -> str:
        """Multi-line human-readable mapping, used for startup logging."""
        if not self.entries:
            return "  (no overlays found)"
        lines = []
        for key in sorted(self.entries.keys()):
            entry = self.entries[key]
            lines.append(
                f"  Alt+{entry.letter.upper()}+{entry.slot}  "
                f"{entry.label:<24}  ({entry.path.name})"
            )
        return "\n".join(lines)
