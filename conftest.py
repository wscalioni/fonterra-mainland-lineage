"""Make `app/` the test import root so `from lib.X import Y` works in tests
just as it does at Databricks Apps runtime.
"""
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
