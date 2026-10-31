"""Put the code being graded on ``sys.path`` before project tests import it.

``practicum grade`` sets ``PRACTICUM_SRC`` to your ``work/`` copy, the starter, or the solution.
"""

import os
import sys
from pathlib import Path

_source = os.environ.get("PRACTICUM_SRC")
if _source is None:
    raise RuntimeError("Run project tests with `pixi run grade <project>` so PRACTICUM_SRC is set.")
sys.path.insert(0, str(Path(_source).resolve()))
