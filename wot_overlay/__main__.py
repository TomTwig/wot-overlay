"""Allow `python -m wot_overlay`."""
import sys

from .app import main

sys.exit(main())
