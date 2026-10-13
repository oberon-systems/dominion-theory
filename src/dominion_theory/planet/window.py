"""
The first window: where on the planet the band era is played.
"""

from collections.abc import Callable

import numpy as np

from ..content import Params
from .noise import stream
from .rivers import Rivers
from .rules import classify, ordered
from .skeleton import Skeleton

STREAM = 'window'
SAMPLE = 32

Place = tuple[int, int]
Judge = Callable[[int, int], int]


def tries(seed: int, params: Params) -> list[Place]:
    """
    The places to try, in the order they are drawn: the north-west cell of each, in cells of the band era.
    """
    window = params.planet.window
    across = params.planet.circumference_km // params.eras.band.cell_km
    down = across // 2
    rng = stream(seed, STREAM)
    columns = rng.integers(0, across - window.width + 1, window.tries)
    latitudes = rng.uniform(window.latitude.min, window.latitude.max, window.tries)
    centres = (1.0 - latitudes) * down / 2
    rows = np.clip(np.floor(centres - window.height / 2), 0, down - window.height)
    return [(int(column), int(row)) for column, row in zip(columns, rows, strict=True)]


def misses(skeleton: Skeleton, rivers: Rivers, params: Params, x: int, y: int) -> int:
    """
    How many needs a window at x, y does not meet, judged on a coarse sample of its cells.
    """
    window = params.planet.window
    needs = window.needs
    cell_km = params.eras.band.cell_km
    columns = min(SAMPLE, window.width)
    rows = min(SAMPLE, window.height)
    east = (x + (np.arange(columns) + 0.5) * window.width / columns) * cell_km
    south = (y + (np.arange(rows) + 0.5) * window.height / rows) * cell_km
    places = np.meshgrid(east, south)
    layers = skeleton.restate(places[0], places[1])
    codes = classify(params.biomes, layers)
    names = ordered(params.biomes)

    met = [float((layers['elevation'] > 0).mean()) >= needs.land]
    met += [float((codes == names.index(name)).mean()) >= share for name, share in needs.biomes.items()]
    lines = rivers.crossing(x * cell_km, y * cell_km, (x + window.width) * cell_km, (y + window.height) * cell_km)
    met.append(lines >= needs.rivers)
    return met.count(False)


def choose(seed: int, params: Params, judge: Judge) -> Place:
    """
    The given place, or the first try the judge finds no fault with, or else the one with the fewest.
    """
    window = params.planet.window
    if window.x is not None and window.y is not None:
        return window.x, window.y

    places = tries(seed, params)
    best = places[0]
    fewest = judge(*best)
    for place in places[1:]:
        if fewest == 0:
            break
        missed = judge(*place)
        if missed < fewest:
            best, fewest = place, missed
    return best
