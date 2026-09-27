"""Compatibility alias for the documentation library harness."""

import sys
from . import _backend

sys.modules[__name__] = _backend("rewrite")
