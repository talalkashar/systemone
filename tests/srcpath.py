"""Put the package source on sys.path.

`python3 -m unittest discover -s labs/systemone/tests` runs from the repo root
and does not set PYTHONPATH. Importing this module makes `systemone` importable
for that command. Subprocess tests still pass PYTHONPATH themselves.
"""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
