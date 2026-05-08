"""Re-export CATEGORY_COLOUR from lib/visualize.py — single source of truth."""
from __future__ import annotations

import importlib.util
from pathlib import Path

# Load the repo-root lib/visualize.py directly by file path. Going via the
# normal `import lib.visualize` machinery doesn't work here because `lib` is
# already bound to this package (`app/lib`) once conftest puts `app/` on
# sys.path — the repo-root `lib/` has no __init__.py and is invisible.
_VISUALIZE_PATH = Path(__file__).resolve().parents[2] / "lib" / "visualize.py"
_spec = importlib.util.spec_from_file_location("_root_visualize", _VISUALIZE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

CATEGORY_COLOUR = _mod.CATEGORY_COLOUR

__all__ = ["CATEGORY_COLOUR"]
