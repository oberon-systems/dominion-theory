"""
Rivers: flow traced on the skeleton, joined into lines in planet kilometres, and the mark they leave on cells.
"""

import heapq
import math
from dataclasses import dataclass
from functools import cached_property, lru_cache
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from ..content import Layer, Temperature
from .noise import Floats, stream
from .skeleton import skeleton

KEPT = 4
STREAM = 'rivers'
NONE = -1
# The eight neighbours as steps south and east, clockwise from the north: the first of two equals wins.
DIRECTIONS = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))
RISE = 1e-9
JITTER = 0.35
PIECES = 4

Flags = NDArray[np.bool_]
Indices = NDArray[np.int64]


def _beside[T: np.generic](grid: NDArray[T], south: int, east: int, beyond: float) -> NDArray[T]:
    """
    For every node the value of its neighbour one step away; x wraps, and past a pole lies beyond.
    """
    turned = np.roll(grid, -east, axis=1)
    if south == 0:
        return turned
    moved = np.full_like(turned, beyond)
    if south > 0:
        moved[:-south] = turned[south:]
    else:
        moved[-south:] = turned[:south]
    return moved


def fill(heights: Floats, land: Flags) -> Floats:
    """
    The heights with hollows filled: every land node gets a lower neighbour on a way down to the sea.
    """
    rows, around = heights.shape
    outlets = ~land
    if not outlets.any():
        outlets.flat[int(heights.argmin())] = True
    pending = land & ~outlets
    shore = np.zeros_like(outlets)
    for south, east in DIRECTIONS:
        shore |= _beside(pending, south, east, False)

    surface: list[float] = heights.ravel().tolist()
    waiting: list[bool] = pending.ravel().tolist()
    heap = [(surface[node], node) for node in np.flatnonzero(outlets & shore).tolist()]
    heapq.heapify(heap)
    while heap:
        level, node = heapq.heappop(heap)
        row, column = divmod(node, around)
        for south, east in DIRECTIONS:
            below = row + south
            if not 0 <= below < rows:
                continue
            beside = below * around + (column + east) % around
            if waiting[beside]:
                waiting[beside] = False
                surface[beside] = max(surface[beside], level + RISE)
                heapq.heappush(heap, (surface[beside], beside))

    filled: Floats = np.array(surface, dtype=np.float64).reshape(heights.shape)
    return filled


def drain(surface: Floats, land: Flags) -> Indices:
    """
    For every land node the flat index of the lowest of its eight neighbours, NONE where nothing lies lower.
    """
    around = surface.shape[1]
    beside = np.stack([_beside(surface, south, east, np.inf) for south, east in DIRECTIONS])
    choice = beside.argmin(axis=0)
    steps = np.array(DIRECTIONS, dtype=np.int64)
    row, column = np.indices(surface.shape)
    targets: Indices = (row + steps[choice, 0]) * around + (column + steps[choice, 1]) % around
    targets[~land | (beside.min(axis=0) >= surface)] = NONE
    return targets


def gather(surface: Floats, targets: Indices, rain: Floats) -> Floats:
    """
    What every node carries: its own rain and all that flows into it. A sea node holds what reached it.
    """
    flow: list[float] = rain.ravel().tolist()
    aims: list[int] = targets.ravel().tolist()
    for node in np.argsort(-surface, axis=None, kind='stable').tolist():
        if aims[node] != NONE:
            flow[aims[node]] += flow[node]
    gathered: Floats = np.array(flow, dtype=np.float64).reshape(rain.shape)
    return gathered


def pick(flow: Floats, surface: Floats, land: Flags, share: float) -> Flags:
    """
    The share of land nodes that carry the most. Of two equals the lower one, so a river is never cut.
    """
    order = np.lexsort((surface.ravel(), -flow.ravel()))
    order = order[land.ravel()[order]][: round(share * int(land.sum()))]
    chosen = np.zeros(flow.size, dtype=bool)
    chosen[order] = True
    return chosen.reshape(flow.shape)


def _stretch(start: Floats, end: Floats, bend: float) -> list[Floats]:
    along = end - start
    across = np.array([-along[1], along[0]]) / float(np.hypot(along[0], along[1]))
    parts = np.arange(1, PIECES) / PIECES
    points = start + along * parts[:, None] + across * (bend * 4 * parts * (1 - parts))[:, None]
    return [*points, end]


def trace(
    flow: Floats,
    targets: Indices,
    chosen: Flags,
    circumference_km: int,
    meander_km: int,
    rng: np.random.Generator,
) -> tuple[Floats, ...]:
    """
    River nodes joined downstream into lines of x, y in kilometres, to the sea or into a larger river.
    """
    rows, around = flow.shape
    side = circumference_km / around
    shifts = rng.uniform(-JITTER, JITTER, (rows, around, 2))
    bends: list[float] = (rng.uniform(-1.0, 1.0, (rows, around)) * meander_km).ravel().tolist()
    centres = np.stack(np.meshgrid(np.arange(around) + 0.5, np.arange(rows) + 0.5), axis=-1)
    places = ((centres + shifts) * side).reshape(-1, 2)

    aims: list[int] = targets.ravel().tolist()
    river: list[bool] = chosen.ravel().tolist()
    nodes = np.flatnonzero(chosen)
    largest: dict[int, int] = {}
    for node in nodes[np.argsort(-flow.ravel()[nodes], kind='stable')].tolist():
        largest.setdefault(aims[node], node)

    lines: list[Floats] = []
    for node in nodes.tolist():
        if node in largest:
            continue
        here = places[node]
        points = [here]
        while aims[node] != NONE:
            after = aims[node]
            there = places[after].copy()
            # The image of the next node nearest to this one, so a line runs on through the seam.
            there[0] += circumference_km * round((here[0] - there[0]) / circumference_km)
            points.extend(_stretch(here, there, bends[node]))
            if not river[after] or largest[after] != node:
                break
            node, here = after, there
        if len(points) > 1:
            lines.append(np.array(points))
    return tuple(lines)


def _crosses(segments: Floats, west: float, north: float, east: float, south: float) -> Flags:
    """
    Which segments touch the rectangle, by clipping every one against its four sides.
    """
    start = segments[:, :2]
    along = segments[:, 2:] - start
    enters = np.zeros(len(segments))
    leaves = np.ones(len(segments))
    inside = np.ones(len(segments), dtype=bool)
    for axis, (low, high) in enumerate(((west, east), (north, south))):
        for step, room in ((-along[:, axis], start[:, axis] - low), (along[:, axis], high - start[:, axis])):
            inside &= (step != 0) | (room >= 0)
            with np.errstate(divide='ignore', invalid='ignore'):
                at = room / step
            enters = np.where(step < 0, np.maximum(enters, at), enters)
            leaves = np.where(step > 0, np.minimum(leaves, at), leaves)
    touched: Flags = inside & (enters <= leaves)
    return touched


def _cells(west: float, north: float, east: float, south: float, cell_km: int) -> set[tuple[int, int]]:
    """
    The cells, as row and column on the planet, that the segment from west, north to east, south crosses.
    """
    cuts = [0.0, 1.0]
    for start, end in ((west, east), (north, south)):
        low, high = min(start, end), max(start, end)
        for line in range(math.floor(low / cell_km) + 1, math.ceil(high / cell_km)):
            cuts.append((line * cell_km - start) / (end - start))
    cuts.sort()
    cells = set()
    for first, second in pairwise(cuts):
        middle = (first + second) / 2
        row = math.floor((north + (south - north) * middle) / cell_km)
        cells.add((row, math.floor((west + (east - west) * middle) / cell_km)))
    return cells


@dataclass(frozen=True)
class Rivers:
    """
    The rivers of a planet: the nodes that carry them, what every node carries, and the lines.
    """

    circumference_km: int
    nodes: Flags
    flow: Floats
    lines: tuple[Floats, ...]

    @cached_property
    def segments(self) -> Floats:
        """
        Every stretch of every line as west, north, east, south of its two ends.
        """
        pieces = [np.hstack((line[:-1], line[1:])) for line in self.lines]
        return np.concatenate(pieces) if pieces else np.zeros((0, 4))

    @cached_property
    def owners(self) -> Indices:
        counts = [len(line) - 1 for line in self.lines]
        return np.repeat(np.arange(len(self.lines), dtype=np.int64), counts)

    def _touching(self, west: float, north: float, east: float, south: float) -> Flags:
        touched = np.zeros(len(self.segments), dtype=bool)
        for turn in (-self.circumference_km, 0, self.circumference_km):
            touched |= _crosses(self.segments + (turn, 0, turn, 0), west, north, east, south)
        return touched

    def crossing(self, west: float, north: float, east: float, south: float) -> int:
        """
        How many lines cross a rectangle given in kilometres.
        """
        return int(np.unique(self.owners[self._touching(west, north, east, south)]).size)

    def marks(self, x: int, y: int, width: int, height: int, cell_km: int) -> Flags:
        """
        For a rectangle of cells, true where a line crosses the cell. A cell is judged by its place alone.
        """
        across = self.circumference_km // cell_km
        west, east = -self.circumference_km, 2 * self.circumference_km
        if width + 2 < across:
            west, east = (x % across - 1) * cell_km, (x % across + width + 1) * cell_km
        near = self._touching(west, (y - 1) * cell_km, east, (y + height + 1) * cell_km)

        ring = np.zeros((height, across), dtype=bool)
        for west, north, east, south in self.segments[near].tolist():
            for row, column in _cells(west, north, east, south, cell_km):
                if y <= row < y + height:
                    ring[row - y, column % across] = True
        marked: Flags = ring[:, (x + np.arange(width)) % across]
        return marked


def lay(
    heights: Floats,
    land: Flags,
    rain: Floats,
    circumference_km: int,
    share: float,
    meander_km: int,
    rng: np.random.Generator,
) -> Rivers:
    """
    The four steps: rain, flow over filled hollows, gathering, the lines.
    """
    surface = fill(heights, land)
    targets = drain(surface, land)
    flow = gather(surface, targets, rain)
    chosen = pick(flow, surface, land, share)
    lines = trace(flow, targets, chosen, circumference_km, meander_km, rng)
    return Rivers(circumference_km=circumference_km, nodes=chosen, flow=flow, lines=lines)


@lru_cache(maxsize=KEPT)
def rivers(
    seed: int,
    circumference_km: int,
    skeleton_km: int,
    sea: float,
    elevation: Layer,
    relief: Layer,
    moisture: Layer,
    temperature: Temperature,
    share: float,
    meander_km: int,
) -> Rivers:
    """
    Kept in the process beside the skeleton they are traced on, never in the state of a game.
    """
    frame = skeleton(seed, circumference_km, skeleton_km, sea, elevation, relief, moisture, temperature)
    return lay(frame.elevation, frame.land, frame.rain, circumference_km, share, meander_km, stream(seed, STREAM))
