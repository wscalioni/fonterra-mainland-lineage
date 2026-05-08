"""Re-export CATEGORY_COLOUR from lib/visualize.py — single source of truth."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.visualize import CATEGORY_COLOUR  # noqa: E402

__all__ = ["CATEGORY_COLOUR"]
