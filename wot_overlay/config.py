"""User-editable configuration.

Everything the user is expected to tweak lives here. No JSON / YAML on purpose:
for a single-file prototype a plain constants module is the simplest thing that
works and is still trivial to change.
"""
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------

# Base directory used to locate the `overlays` folder.
#
# - When running from source  -> project root (repo checkout)
# - When running as a frozen PyInstaller build -> folder that contains the
#   `wot-overlay.exe` file, so the expected layout for end users is:
#
#       wot-overlay\
#           wot-overlay.exe
#           overlays\
#               paris_1.png
#               ...
#
# This keeps the runtime layout identical for every user.
if getattr(sys, "frozen", False):
    _BASE_DIR: Path = Path(sys.executable).resolve().parent
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

OVERLAYS_DIR: Path = _BASE_DIR / "overlays"


# ----------------------------------------------------------------------------
# Overlay window geometry
# ----------------------------------------------------------------------------

# Edge length of the square overlay, in pixels.
# WoT's in-game minimap is square, so we render into a square window.
OVERLAY_SIZE: int = 512

# Distance from the right edge of the primary screen, in pixels.
OFFSET_RIGHT: int = 0

# Distance from the bottom edge of the primary screen, in pixels.
OFFSET_BOTTOM: int = 0


# ----------------------------------------------------------------------------
# Opacity
# ----------------------------------------------------------------------------

DEFAULT_OPACITY: float = 0.50   # 0.0 - 1.0
OPACITY_STEP: float = 0.10
MIN_OPACITY: float = 0.10
MAX_OPACITY: float = 1.00


# ----------------------------------------------------------------------------
# Status "toast" display
# ----------------------------------------------------------------------------

# How long status messages stay visible before auto-hiding.
STATUS_DURATION_MS: int = 1500

# Distance from the top of the primary screen, in pixels.
STATUS_OFFSET_TOP: int = 40


# ----------------------------------------------------------------------------
# Hotkeys
# ----------------------------------------------------------------------------
#
# Syntax follows the `keyboard` library:
#   - `+` joins keys that must be pressed together (a chord).
#   - `,` joins keys that must be pressed in sequence.
#
# Per-overlay selection hotkeys are built automatically as
# `alt+<letter>+<slot>` from the files found in OVERLAYS_DIR.
#
# Note: if you ever add an overlay whose map name starts with the same letter
# as the toggle hotkey (default `o`), the chord `alt+o+N` and the toggle
# `alt+o` will both fire. Change HOTKEY_TOGGLE to e.g. `alt+shift+o` in that
# case.

HOTKEY_TOGGLE: str = "alt+o"       # show / hide the overlay
HOTKEY_CLEAR: str = "alt+0"        # clear the current image
HOTKEY_OPACITY_UP: str = "alt+="   # physical `=` / `+` key on main keyboard
HOTKEY_OPACITY_DOWN: str = "alt+-"


# ----------------------------------------------------------------------------
# Startup behaviour
# ----------------------------------------------------------------------------

# If True, the overlay window is created but hidden until the user either
# presses HOTKEY_TOGGLE or selects an image.
START_HIDDEN: bool = False
