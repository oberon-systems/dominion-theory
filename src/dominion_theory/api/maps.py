"""
A rectangle of the map, in planet coordinates of the window's scale.
"""

from typing import Any

import numpy as np

from ..engine import Game


def _span(start: int | None, size: int | None, low: int, extent: int) -> tuple[int, int]:
    first = low if start is None else start
    last = first + (extent if size is None else size)
    first = min(max(first, low), low + extent)
    return first, max(min(last, low + extent), first)


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
    window = game.window
    left, right = _span(x, width, window.x, window.width)
    top, bottom = _span(y, height, window.y, window.height)
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
        'scale': window.scale,
        'x': left,
        'y': top,
        'width': right - left,
        'height': bottom - top,
        'biomes': [names[code] for code in codes.tolist()],
        'cells': cells.ravel().tolist(),
        'rivers': game.rivers[rows, columns].astype(int).ravel().tolist(),
        **{name: stock.ravel().tolist() for name, stock in stocks.items()},
    }
