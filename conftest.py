"""Pytest bootstrap: ensure repo root is on sys.path so `app.lib.*` imports resolve.

`app/` is intentionally not a package (no __init__.py) so the Dash entrypoint
can run as a module from inside the bundle. This conftest at the repo root
prepends the repo path so `from app.lib import ...` works under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
