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
# Hotkey syntax follows the `keyboard` library:
#   - `+` joins keys that must be pressed together (a chord).
#   - `,` joins keys that must be pressed in sequence.
#
# Selection flow
# ~~~~~~~~~~~~~~
# The picker uses a hold-modifier workflow. Hold ``PICKER_MODIFIER`` (by
# default `tab`) and tap the first letter of a map name to open a picker
# showing all overlays starting with that letter. Tapping the same letter
# again cycles through the list. Releasing the modifier applies the
# currently highlighted entry.
#
# Per-letter chords ``<PICKER_MODIFIER>+<letter>`` are registered
# automatically from the files in OVERLAYS_DIR — you never have to list
# them here.
#
# Overlay toggle
# ~~~~~~~~~~~~~~
# ``HOTKEY_TOGGLE`` is special: if it contains no ``+``, it is treated as a
# single key and fires only on a *clean tap* (key pressed and released with
# no other key pressed in between). That keeps ``alt`` usable as both a
# toggle **and** a modifier for ``alt+shift+q`` etc. — the toggle only
# fires if Alt is tapped alone.
#
# If HOTKEY_TOGGLE contains ``+`` it's treated as a normal chord, same as
# the other HOTKEY_* constants.

# Key to hold while tapping a letter to open the picker.
PICKER_MODIFIER: str = "tab"

HOTKEY_TOGGLE: str = "alt"           # single key  -> tap to toggle overlay
HOTKEY_CLEAR: str = "alt+0"          # clear the current image
HOTKEY_OPACITY_UP: str = "alt+="     # physical `=` / `+` key on main keyboard
HOTKEY_OPACITY_DOWN: str = "alt+-"
HOTKEY_QUIT: str = "alt+shift+q"     # cleanly exit the app (no taskbar icon
                                     # exists, so this is the only way out)


# ----------------------------------------------------------------------------
# Startup behaviour
# ----------------------------------------------------------------------------

# If True, the overlay window is created but hidden until the user either
# presses HOTKEY_TOGGLE or selects an image.
START_HIDDEN: bool = False


# ============================================================================
# Runtime config file (`config.json`) — end users don't rebuild the exe.
# ============================================================================
#
# Any key present in `config.json` overrides the matching default above. The
# file lives next to the exe (or next to the project root when running from
# source), so the expected layout for end users is:
#
#       wot-overlay\
#           wot-overlay.exe
#           config.json          <-- this file
#           overlays\
#               paris_1.png
#               ...
#
# On first launch the file is created automatically with the current defaults
# so users have a template to edit. Unknown keys, wrong types, and values
# outside the allowed range are logged and ignored — a typo can never prevent
# the app from starting.

import json as _json

CONFIG_FILE: Path = _BASE_DIR / "config.json"


def _nonempty_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _single_key(v: object) -> bool:
    # Picker modifier must be a single key name (no chord).
    return _nonempty_str(v) and "+" not in v  # type: ignore[operator]


# JSON key -> (python constant name, allowed type(s), validator)
_USER_OVERRIDES = {
    "overlay_size":        ("OVERLAY_SIZE",        int,          lambda v: v > 0),
    "offset_right":        ("OFFSET_RIGHT",        int,          lambda v: v >= 0),
    "offset_bottom":       ("OFFSET_BOTTOM",       int,          lambda v: v >= 0),
    "default_opacity":     ("DEFAULT_OPACITY",     (int, float), lambda v: 0.0 <= v <= 1.0),
    "picker_modifier":     ("PICKER_MODIFIER",     str,          _single_key),
    "hotkey_toggle":       ("HOTKEY_TOGGLE",       str,          _nonempty_str),
    "hotkey_clear":        ("HOTKEY_CLEAR",        str,          _nonempty_str),
    "hotkey_opacity_up":   ("HOTKEY_OPACITY_UP",   str,          _nonempty_str),
    "hotkey_opacity_down": ("HOTKEY_OPACITY_DOWN", str,          _nonempty_str),
    "hotkey_quit":         ("HOTKEY_QUIT",         str,          _nonempty_str),
}


def _write_default_config_file() -> None:
    template = {
        "overlay_size":        OVERLAY_SIZE,
        "offset_right":        OFFSET_RIGHT,
        "offset_bottom":       OFFSET_BOTTOM,
        "default_opacity":     DEFAULT_OPACITY,
        "picker_modifier":     PICKER_MODIFIER,
        "hotkey_toggle":       HOTKEY_TOGGLE,
        "hotkey_clear":        HOTKEY_CLEAR,
        "hotkey_opacity_up":   HOTKEY_OPACITY_UP,
        "hotkey_opacity_down": HOTKEY_OPACITY_DOWN,
        "hotkey_quit":         HOTKEY_QUIT,
    }
    try:
        CONFIG_FILE.write_text(
            _json.dumps(template, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[wot-overlay] Created default config at: {CONFIG_FILE}")
    except OSError as exc:
        print(f"[wot-overlay] Could not write {CONFIG_FILE}: {exc}")


def _apply_user_config() -> None:
    if not CONFIG_FILE.exists():
        _write_default_config_file()
        return

    try:
        data = _json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        print(f"[wot-overlay] Failed to read {CONFIG_FILE}: {exc}")
        print("[wot-overlay] Falling back to built-in defaults.")
        return

    if not isinstance(data, dict):
        print(
            f"[wot-overlay] {CONFIG_FILE.name}: top-level value must be a JSON object"
        )
        return

    for key, value in data.items():
        if key not in _USER_OVERRIDES:
            print(f"[wot-overlay] {CONFIG_FILE.name}: unknown key {key!r} (ignored)")
            continue
        const_name, expected_type, validator = _USER_OVERRIDES[key]
        # Reject bools explicitly — in Python, bool is a subclass of int, and
        # `true` / `false` in JSON would otherwise sneak through isinstance().
        if isinstance(value, bool) or not isinstance(value, expected_type):
            print(
                f"[wot-overlay] {CONFIG_FILE.name}: {key!r} has wrong type "
                f"(expected {expected_type}, got {type(value).__name__})"
            )
            continue
        if not validator(value):
            print(
                f"[wot-overlay] {CONFIG_FILE.name}: {key!r} value {value!r} "
                "is out of the allowed range"
            )
            continue
        globals()[const_name] = value
        print(f"[wot-overlay] config.json override: {key} = {value}")


_apply_user_config()
