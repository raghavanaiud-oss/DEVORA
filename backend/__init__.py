import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_root_dir = _pkg_dir.parent
for _p in (str(_root_dir), str(_pkg_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
