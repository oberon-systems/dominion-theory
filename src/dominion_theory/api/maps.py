"""
A rectangle of the map, in planet coordinates of the window's scale: as it is, or as a band knows it.
"""

from typing import Any

import numpy as np

from ..core.errors import DominionError
from ..engine import Game
from .errors import UNIT_NOT_FOUND

SEEN = 'seen'


def _span(start: int | None, size: int | None, low: int, extent: int) -> tuple[int, int]:
    first = low if start is None else start
    last = first + (extent if size is None else size)
    first = min(max(first, low), low + extent)
    return first, max(min(last, low + extent), first)


def _bounds(game: Game, x: int | None, y: int | None, width: int | None, height: int | None) -> dict[str, int]:
    window = game.window
    left, right = _span(x, width, window.x, window.width)
    top, bottom = _span(y, height, window.y, window.height)
    return {'scale': window.scale, 'x': left, 'y': top, 'width': right - left, 'height': bottom - top}


def rectangle(
    game: Game,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """
    The part of the asked rectangle that lies in the window; what is left out is all of the window.
    """
    window, bounds = game.window, _bounds(game, x, y, width, height)
    left, top, right, bottom = bounds['x'], bounds['y'], bounds['x'] + bounds['width'], bounds['y'] + bounds['height']
    rows, columns = slice(top - window.y, bottom - window.y), slice(left - window.x, right - window.x)
    codes, cells = np.unique(game.biomes[rows, columns], return_inverse=True)
    stocks = {name: np.ones((bottom - top, right - left)) for name in game.stocked}
    for kept in game.cells.plain():
        at = kept['x'], kept['y']
        if left <= at[0] < right and top <= at[1] < bottom:
            for name, stock in stocks.items():
                stock[at[1] - top, at[0] - left] = game.cells.stock(at, name)
    names = game.snapshot()['biomes']
    return {
        **bounds,
        'biomes': [names[code] for code in codes.tolist()],
        'cells': cells.ravel().tolist(),
        'rivers': game.rivers[rows, columns].astype(int).ravel().tolist(),
        **{name: stock.ravel().tolist() for name, stock in stocks.items()},
    }


def remembered(
    game: Game,
    unit: int,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """
    The same rectangle as the band of that id remembers it: null in every list where it knows nothing.
    """
    band = game.band
    if band is None or band.id != unit:
        raise DominionError(UNIT_NOT_FOUND, id=unit)
    bounds = _bounds(game, x, y, width, height)
    known = [
        band.known.get((column, row))
        for row in range(bounds['y'], bounds['y'] + bounds['height'])
        for column in range(bounds['x'], bounds['x'] + bounds['width'])
    ]
    names = game.snapshot()['biomes']
    present = {cell['biome'] for cell in known if cell is not None}
    biomes = [name for name in names if name in present]
    index = {name: code for code, name in enumerate(biomes)}
    lists = (*game.params.eras[game.era].properties, SEEN)
    return {
        **bounds,
        'biomes': biomes,
        'cells': [None if cell is None else index[cell['biome']] for cell in known],
        'rivers': [None if cell is None else int(cell['river']) for cell in known],
        **{name: [None if cell is None else cell[name] for cell in known] for name in lists},
    }
