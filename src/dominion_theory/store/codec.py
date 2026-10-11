"""
The encoding of a snapshot: a JSON document, then the grids as compressed arrays.
"""

import json
import math
import struct
import zlib
from typing import Any

import numpy as np

GRIDS = 'grids'
HEAD = struct.Struct('>I')


def dumps(document: object) -> bytes:
    return json.dumps(document, separators=(',', ':')).encode()


def pack(snapshot: dict[str, Any]) -> bytes:
    grids = {name: np.ascontiguousarray(grid) for name, grid in snapshot.get(GRIDS, {}).items()}
    head = dumps(
        {
            'state': {name: value for name, value in snapshot.items() if name != GRIDS},
            'grids': [
                {'name': name, 'dtype': grid.dtype.str, 'shape': list(grid.shape)} for name, grid in grids.items()
            ],
        }
    )
    body = zlib.compress(b''.join(grid.tobytes() for grid in grids.values()))
    return HEAD.pack(len(head)) + head + body


def unpack(data: bytes) -> dict[str, Any]:
    (size,) = HEAD.unpack_from(data)
    document = json.loads(data[HEAD.size : HEAD.size + size])
    body = zlib.decompress(data[HEAD.size + size :])
    grids = {}
    offset = 0
    for held in document['grids']:
        dtype = np.dtype(held['dtype'])
        count = math.prod(held['shape'])
        grids[held['name']] = np.frombuffer(body, dtype, count, offset).reshape(held['shape']).copy()
        offset += count * dtype.itemsize
    return {**document['state'], GRIDS: grids}
