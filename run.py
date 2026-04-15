"""Convenience entrypoint: `python run.py`."""
import sys

from wot_overlay.app import main

if __name__ == "__main__":
    sys.exit(main())
