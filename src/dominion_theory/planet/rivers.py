"""
Rivers: flow traced on the skeleton, joined into lines in planet kilometres, and the mark they leave on cells.
With them the lakes that stand in hollows on the way, and the flow as a layer for the rules of biomes.
"""

import heapq
import math
from dataclasses import dataclass
from functools import cached_property, lru_cache
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from ..content import Elevation, Layer, Temperature
from .noise import Floats, stream
from .skeleton import Skeleton, skeleton

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


def ocean(land: Flags, share: float) -> Flags:
    """
    The sea nodes that lie in a body of water holding at least a share of all of them. A smaller body is
    an inland sea: water runs through it and on, as through a lake.
    """
    rows, around = land.shape
    body = [0 if dry else NONE for dry in land.ravel().tolist()]
    sizes = [0]
    for start in np.flatnonzero(~land).tolist():
        if body[start] != NONE:
            continue
        body[start] = len(sizes)
        reached = [start]
        for node in reached:
            row, column = divmod(node, around)
            for south, east in DIRECTIONS:
                below = row + south
                beside = below * around + (column + east) % around
                if 0 <= below < rows and body[beside] == NONE:
                    body[beside] = len(sizes)
                    reached.append(beside)
        sizes.append(len(reached))

    least = share * (land.size - int(land.sum()))
    open_sea = np.array([number > 0 and size >= least for number, size in enumerate(sizes)], dtype=bool)
    wide: Flags = open_sea[np.array(body, dtype=np.int64)].reshape(land.shape)
    return wide


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


def sources(chosen: Flags, flow: Floats, targets: Indices) -> Flags:
    """
    The chosen nodes and, above each, the largest inflow followed up to where nothing flows in: its source.
    """
    aims: list[int] = targets.ravel().tolist()
    largest: dict[int, int] = {}
    for node in np.argsort(-flow, axis=None, kind='stable').tolist():
        if aims[node] != NONE:
            largest.setdefault(aims[node], node)

    marked: list[bool] = chosen.ravel().tolist()
    for node in np.flatnonzero(chosen).tolist():
        above = largest.get(node)
        while above is not None and not marked[above]:
            marked[above] = True
            above = largest.get(above)
    followed: Flags = np.array(marked, dtype=bool).reshape(chosen.shape)
    return followed


def flooded(heights: Floats, surface: Floats, land: Flags, share: float) -> Floats:
    """
    The level of the lake at every node: of the hollows the deepest share hold one, the rest of the land none.
    """
    depth = np.where(land, surface - heights, 0.0).ravel()
    hollows = np.flatnonzero(depth > 0)
    deepest = hollows[np.argsort(-depth[hollows], kind='stable')][: round(share * hollows.size)]
    levels = np.full(heights.size, -np.inf)
    levels[deepest] = surface.ravel()[deepest]
    return levels.reshape(heights.shape)


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
    land: Flags,
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
    # A sea node stays at its centre, which is under water at any cell size, so a mouth never ends on land.
    shifts[~land] = 0.0
    bends: list[float] = (rng.uniform(-1.0, 1.0, (rows, around)) * meander_km).ravel().tolist()
    centres = np.stack(np.meshgrid(np.arange(around) + 0.5, np.arange(rows) + 0.5), axis=-1)
    places = ((centres + shifts) * side).reshape(-1, 2)

    aims: list[int] = targets.ravel().tolist()
    river: list[bool] = chosen.ravel().tolist()
    nodes = np.flatnonzero(chosen)
    largest: dict[int, int] = {}
    for node in nodes[np.argsort(-flow.ravel()[nodes], kind='stable')].tolist():
        largest.setdefault(aims[node], node)
    # An inland sea spills into the node below it, and the river that leaves it starts on its water.
    spills: dict[int, int] = {}
    for node in np.flatnonzero(~land).tolist():
        if aims[node] != NONE:
            spills.setdefault(aims[node], node)

    lines: list[Floats] = []
    for node in nodes.tolist():
        if node in largest:
            continue
        here = places[node]
        points = [here]
        if node in spills:
            water = places[spills[node]].copy()
            water[0] += circumference_km * round((here[0] - water[0]) / circumference_km)
            points = [water, here]
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
    The rivers of a planet: the nodes that carry them, what every node carries, the lines,
    the level of the lake at every node and the flow of every node as a share of land.
    """

    circumference_km: int
    nodes: Flags
    flow: Floats
    lines: tuple[Floats, ...]
    levels: Floats
    shares: Floats

    def lake(self, x: Floats, y: Floats) -> Floats:
        """
        The level of the lake a place in kilometres may lie in: the highest of the four nodes around it,
        and no level where none of them holds a lake.
        """
        rows, around = self.levels.shape
        side = self.circumference_km / around
        column = np.floor(x / side - 0.5).astype(np.int64)
        row = np.clip(np.floor(y / side - 0.5).astype(np.int64), 0, rows - 1)
        below = np.minimum(row + 1, rows - 1)
        west, east = column % around, (column + 1) % around
        level: Floats = np.maximum.reduce(
            [self.levels[row, west], self.levels[row, east], self.levels[below, west], self.levels[below, east]]
        )
        return level

    def wet(self, x: Floats, y: Floats) -> Floats:
        """
        The flow at a place in kilometres, 0 to 1, read between the four nodes around it.
        """
        rows, around = self.shares.shape
        side = self.circumference_km / around
        east = x / side - 0.5
        south = np.clip(y / side - 0.5, 0.0, rows - 1.0)
        column = np.floor(east).astype(np.int64)
        row = np.minimum(np.floor(south).astype(np.int64), max(rows - 2, 0))
        below = np.minimum(row + 1, rows - 1)
        along, down = east - column, south - row
        north = self.shares[row, column % around] * (1 - along) + self.shares[row, (column + 1) % around] * along
        further = self.shares[below, column % around] * (1 - along) + self.shares[below, (column + 1) % around] * along
        read: Floats = north * (1 - down) + further * down
        return read

    def restate(self, frame: Skeleton, x: Floats, y: Floats) -> dict[str, Floats]:
        """
        Every layer the rules of biomes read at places in kilometres: those of the skeleton, lakes and flow laid in.
        """
        return {**frame.restate(x, y, self.lake(x, y)), 'flow': self.wet(x, y)}

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
    lakes: float,
    open_sea: float,
    meander_km: int,
    rng: np.random.Generator,
) -> Rivers:
    """
    The steps: rain, flow over filled hollows, gathering, rivers followed up to their sources, the lines.
    Water leaves the land and the inland seas alike: only the ocean keeps it.
    """
    inland = ~ocean(land, open_sea)
    surface = fill(heights, inland)
    targets = drain(surface, inland)
    flow = gather(surface, targets, rain)
    chosen = sources(pick(flow, surface, land, share), flow, targets)
    lines = trace(flow, targets, chosen, land, circumference_km, meander_km, rng)
    carried = np.sort(flow[land]) if land.any() else np.zeros(1)
    return Rivers(
        circumference_km=circumference_km,
        nodes=chosen,
        flow=flow,
        lines=lines,
        levels=flooded(heights, surface, land, lakes),
        shares=np.interp(flow, carried, np.linspace(0.0, 1.0, carried.size)),
    )


@lru_cache(maxsize=KEPT)
def rivers(
    seed: int,
    circumference_km: int,
    skeleton_km: int,
    sea: float,
    elevation: Elevation,
    relief: Layer,
    moisture: Layer,
    temperature: Temperature,
    share: float,
    lakes: float,
    open_sea: float,
    meander_km: int,
) -> Rivers:
    """
    Kept in the process beside the skeleton they are traced on, never in the state of a game.
    """
    frame = skeleton(seed, circumference_km, skeleton_km, sea, elevation, relief, moisture, temperature)
    rng = stream(seed, STREAM)
    return lay(frame.elevation, frame.land, frame.rain, circumference_km, share, lakes, open_sea, meander_km, rng)
