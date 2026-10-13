"""
Dominion Theory: Maps: Tools: Pictures

    A picture is an array of rows, columns and three colours, made from what the planet answers.
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from ...content import Params
from .. import Region, biome_names

RIVER = '#7FDBFF'
FRAME = '#FF2D2D'
GAP = '#282828'
LOW = '#101028'
HIGH = '#FFE66D'
PADDING = 4
LONG = 8
DEPTH = 0.6

Picture = NDArray[np.uint8]
Values = NDArray[np.float64]


def rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def biomes(params: Params, region: Region) -> Picture:
    """
    Every cell in the colour of its biome, the cells a river crosses in the colour of rivers.
    """
    names = biome_names(params)
    palette = np.array([rgb(params.biomes[name].colour) for name in names], dtype=np.uint8)
    # Open water is painted darker the deeper it lies; water that is frozen keeps its colour.
    rules = [params.biomes[name].generation for name in names]
    sea = [rule.elevation is not None and rule.elevation.max is not None and rule.elevation.max <= 0 for rule in rules]
    open_water = np.array([wet and rule.temperature is None for wet, rule in zip(sea, rules, strict=True)])
    deep = np.where(open_water[region.biomes], np.clip(-region.elevation, 0.0, 1.0), 0.0)
    picture: Picture = np.rint(palette[region.biomes] * (1.0 - DEPTH * deep[..., None])).astype(np.uint8)
    picture[region.rivers] = rgb(RIVER)
    return picture


def values(params: Params, era: str, name: str, region: Region, season: str | None = None) -> Values:
    """
    A property over the cells: (base + every plus) * every times, held in 0..1, with every stock full.
    """
    names = biome_names(params)
    plus = np.zeros(len(names))
    times = np.ones(len(names))
    for code, biome in enumerate(names):
        held = params.biomes[biome].eras[era].properties[name]
        plus[code] = held.base
        modifier = held.seasons.get(season) if season else None
        if modifier is not None and modifier.kind == 'plus':
            plus[code] += modifier.amount
        elif modifier is not None:
            times[code] *= modifier.amount

    added, multiplied = plus[region.biomes], times[region.biomes]
    river = params.planet.rivers.effects.get(era, {}).get(name)
    if river is not None and river.kind == 'plus':
        added = added + np.where(region.rivers, river.amount, 0.0)
    elif river is not None:
        multiplied = multiplied * np.where(region.rivers, river.amount, 1.0)
    worked: Values = np.clip(added * multiplied, 0.0, 1.0)
    return worked


def shaded(amounts: Values) -> Picture:
    """
    Values of 0..1 as colours, from the dark of nothing to the bright of everything.
    """
    low, high = np.array(rgb(LOW), dtype=np.float64), np.array(rgb(HIGH), dtype=np.float64)
    picture: Picture = np.rint(low + (high - low) * amounts[..., None]).astype(np.uint8)
    return picture


def tiled(pictures: Sequence[Picture]) -> Picture:
    """
    Pictures of one size side by side, two in a row.
    """
    height, width = pictures[0].shape[:2]
    rows = (len(pictures) + 1) // 2
    sheet = np.empty((rows * height + (rows + 1) * PADDING, 2 * width + 3 * PADDING, 3), dtype=np.uint8)
    sheet[:] = rgb(GAP)
    for position, picture in enumerate(pictures):
        top = PADDING + (position // 2) * (height + PADDING)
        left = PADDING + (position % 2) * (width + PADDING)
        sheet[top : top + height, left : left + width] = picture
    return sheet


def framed(picture: Picture, x: int, y: int, width: int, height: int) -> Picture:
    """
    The picture with the outline of a rectangle of its cells, as the first window on the planet.
    """
    drawn = picture.copy()
    rows, columns = drawn.shape[:2]
    top, bottom = max(y, 0), min(y + height, rows) - 1
    left, right = max(x, 0), min(x + width, columns) - 1
    drawn[top, left : right + 1] = drawn[bottom, left : right + 1] = rgb(FRAME)
    drawn[top : bottom + 1, left] = drawn[top : bottom + 1, right] = rgb(FRAME)
    return drawn


def enlarged(picture: Picture, scale: int) -> Picture:
    grown: Picture = np.repeat(np.repeat(picture, scale, axis=0), scale, axis=1)
    return grown


def _runs(edges: NDArray[np.bool_]) -> NDArray[np.int64]:
    """
    For every edge along a row, how many edges in a row it stands with.
    """
    padded = np.zeros((edges.shape[0], edges.shape[1] + 2), dtype=np.int8)
    padded[:, 1:-1] = edges
    steps = np.diff(padded.ravel())
    spans = np.flatnonzero(steps == -1) - np.flatnonzero(steps == 1)
    lengths = np.zeros(padded.size, dtype=np.int64)
    lengths[padded.ravel() == 1] = np.repeat(spans, spans)
    held: NDArray[np.int64] = lengths.reshape(padded.shape)[:, 1:-1]
    return held


def corners(water: NDArray[np.bool_]) -> int:
    """
    How many square corners the shore has: places where a straight stretch of it running east meets one
    running south, both LONG cells or longer. A shore that follows the land has none; one cut by a grid has many.
    """
    if min(water.shape) < 2:
        return 0
    east = _runs(water[:-1] != water[1:]) >= LONG
    south = _runs((water[:, :-1] != water[:, 1:]).T).T >= LONG
    return int(((east[:, :-1] | east[:, 1:]) & (south[:-1] | south[1:])).sum())


def shares(params: Params, region: Region) -> dict[str, float]:
    """
    The share of the cells every biome takes, in the order of generation.
    """
    counts = np.bincount(region.biomes.ravel(), minlength=len(biome_names(params)))
    return {name: float(count) / region.biomes.size for name, count in zip(biome_names(params), counts, strict=True)}
