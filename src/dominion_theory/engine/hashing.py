"""
The hash of a state: the same on every run and platform, with numbers rounded first.
"""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

PLACES = 6


def _rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, PLACES) + 0.0
    if isinstance(value, Mapping):
        return {str(name): _rounded(item) for name, item in value.items()}
    if isinstance(value, list | tuple):
        return [_rounded(item) for item in value]
    return value


def digest(plain: Mapping[str, Any], grids: Mapping[str, NDArray[Any]]) -> str:
    canonical = json.dumps(_rounded(plain), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    found = hashlib.sha256(canonical.encode())
    for name in sorted(grids):
        grid = grids[name]
        if grid.dtype.kind == 'f':
            grid = np.round(grid, PLACES) + 0.0
        fixed = np.ascontiguousarray(grid, dtype=grid.dtype.newbyteorder('<'))
        found.update(f'{name}:{fixed.dtype.str}:{fixed.shape}'.encode())
        found.update(fixed.tobytes())
    return found.hexdigest()
