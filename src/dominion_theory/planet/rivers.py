"""
Rivers: flow traced on the skeleton, joined into lines in planet kilometres, and the mark they leave on cells.
With them the lakes that stand in hollows on the way, the beds of the great rivers, and the flow as a layer
for the rules of biomes.
"""

import heapq
import math
from collections.abc import Callable, Mapping
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
PIECES = 3
STRIDE = 10.0
SMALLEST = 1e-12

Flags = NDArray[np.bool_]
Indices = NDArray[np.int64]
Under = Callable[[Floats, Floats], Flags]


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


def _bodies(held: Flags) -> tuple[Indices, list[int]]:
    """
    The nodes that hold, gathered into bodies of neighbours: the number of the body of every node, from 1,
    with 0 for a node that does not hold, and the size of every body by its number.
    """
    rows, around = held.shape
    body = [NONE if holds else 0 for holds in held.ravel().tolist()]
    sizes = [0]
    for start in np.flatnonzero(held).tolist():
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
    return np.array(body, dtype=np.int64).reshape(held.shape), sizes


def ocean(land: Flags, share: float) -> Flags:
    """
    The sea nodes that lie in a body of water holding at least a share of all of them. A smaller body is
    an inland sea: water runs through it and on, as through a lake.
    """
    bodies, sizes = _bodies(~land)
    least = share * (land.size - int(land.sum()))
    open_sea = np.array([number > 0 and size >= least for number, size in enumerate(sizes)], dtype=bool)
    wide: Flags = open_sea[bodies]
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


def flooded(heights: Floats, surface: Floats, land: Flags, share: float) -> Flags:
    """
    The nodes that hold a lake. Hollows that touch are one basin, and of the basins the deepest share is flooded,
    each as a whole.
    """
    depth = np.where(land, surface - heights, 0.0)
    bodies, sizes = _bodies(depth > 0)
    deepest = np.zeros(len(sizes))
    np.maximum.at(deepest, bodies.ravel(), depth.ravel())
    order = np.argsort(-deepest[1:], kind='stable') + 1
    kept = np.zeros(len(sizes), dtype=bool)
    kept[order[: round(share * (len(sizes) - 1))]] = True
    holding: Flags = kept[bodies]
    return holding


def _smooth(controls: Floats) -> Floats:
    """
    A curve through every point given, drawn in PIECES stretches between two of them, with no corner at a point.
    """
    last = len(controls) - 1
    parts = (np.arange(1, PIECES) / PIECES)[:, None]
    points = [controls[:1]]
    for start in range(last):
        before, here = controls[max(start - 1, 0)], controls[start]
        there, after = controls[start + 1], controls[min(start + 2, last)]
        bent = 0.5 * (
            2 * here
            + (there - before) * parts
            + (2 * before - 5 * here + 4 * there - after) * parts**2
            + (3 * here - before - 3 * there + after) * parts**3
        )
        points += [bent, there[None, :]]
    curve: Floats = np.concatenate(points)
    return curve


def _arm(start: Floats, heading: float, turn: float, reach: float, under: Under) -> Floats | None:
    """
    One arm of a delta: from its start it bears away from the river more and more, a stride at a time,
    and ends at the first place under the sea. An arm that finds no sea within its reach is not drawn.
    """
    count = max(int(reach / STRIDE), 1)
    headings = heading + turn * np.linspace(0.3, 1.0, count)
    points = start + np.cumsum(STRIDE * np.column_stack((np.cos(headings), np.sin(headings))), axis=0)
    wet = under(points[:, 0], points[:, 1])
    if not wet.any():
        return None
    arm: Floats = np.vstack((start[None, :], points[: int(wet.argmax()) + 1]))
    return arm


def delta(apex: Floats, mouth: Floats, course: Mapping[str, float], forks: Floats, under: Under) -> list[Floats]:
    """
    The arms a great river breaks into before the ocean: a fan from its apex, as wide at the mouth
    as delta_km, every arm forking once on its way.
    """
    along = mouth - apex
    reach = float(np.hypot(along[0], along[1]))
    heading = float(np.arctan2(along[1], along[0]))
    spread = float(np.arctan2(course['delta_km'] / 2, reach))
    arms: list[Floats] = []
    for number, turn in enumerate(np.linspace(-spread, spread, int(course['arms'])).tolist()):
        arm = None if abs(turn) < SMALLEST else _arm(apex, heading, turn, 2.5 * reach, under)
        if arm is None:
            continue
        arms.append(arm)
        split = int((len(arm) - 1) * (0.35 + 0.3 * forks[number, 0]))
        if split < 1:
            continue
        before = arm[split] - arm[split - 1]
        aside = (1.0 if forks[number, 1] < 0.5 else -1.0) * 2 * spread / max(int(course['arms']), 1)
        fork = _arm(arm[split], float(np.arctan2(before[1], before[0])), aside, 2.5 * reach, under)
        if fork is not None:
            arms.append(fork)
    return arms


def trace(
    flow: Floats,
    targets: Indices,
    chosen: Flags,
    great: Flags,
    land: Flags,
    open_sea: Flags,
    sizes: Floats,
    circumference_km: int,
    course: Mapping[str, float],
    rng: np.random.Generator,
    under: Under | None = None,
) -> tuple[tuple[Floats, ...], Floats]:
    """
    River nodes joined downstream into lines of x, y in kilometres, to the sea or into a larger river,
    and every stretch of them as a row: its two ends, half the width of the bed at each, the size of the
    river at each. Where under tells what lies beneath the sea, a great river meets the ocean in a delta.
    """
    rows, around = flow.shape
    side = circumference_km / around
    shifts = rng.uniform(-JITTER, JITTER, (rows, around, 2))
    # A sea node stays at its centre, which is under water at any cell size, so a mouth never ends on land.
    shifts[~land] = 0.0
    bends: list[float] = (rng.uniform(-1.0, 1.0, (rows, around)) * course['meander_km']).ravel().tolist()
    centres = np.stack(np.meshgrid(np.arange(around) + 0.5, np.arange(rows) + 0.5), axis=-1)
    places = ((centres + shifts) * side).reshape(-1, 2)
    narrow = course['width_km'] / 2
    forks = rng.uniform(0.0, 1.0, (rows * around, max(int(course['arms']), 1), 2))

    aims: list[int] = targets.ravel().tolist()
    river: list[bool] = chosen.ravel().tolist()
    broad: list[bool] = great.ravel().tolist()
    carried: list[float] = sizes.ravel().tolist()
    ocean_at: list[bool] = open_sea.ravel().tolist()
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
    courses: list[Floats] = []
    for node in nodes.tolist():
        if node in largest:
            continue
        here = places[node]
        controls = [here]
        halves = [narrow if broad[node] else 0.0]
        grown = [carried[node]]
        if node in spills:
            water = places[spills[node]].copy()
            water[0] += circumference_km * round((here[0] - water[0]) / circumference_km)
            controls.insert(0, water)
            halves.insert(0, halves[0])
            grown.insert(0, grown[0])
        above = here
        while aims[node] != NONE:
            after = aims[node]
            there = places[after].copy()
            # The image of the next node nearest to this one, so a line runs on through the seam.
            there[0] += circumference_km * round((here[0] - there[0]) / circumference_km)
            along = there - here
            across = np.array([-along[1], along[0]]) / float(np.hypot(along[0], along[1]))
            half = narrow if broad[node] else 0.0
            controls += [(here + there) / 2 + across * bends[node], there]
            halves += [half, half]
            grown += [carried[node], carried[node]]
            if under is not None and broad[node] and ocean_at[after]:
                # The fan opens a node above the last one on land, so the arms have room to part and fork.
                for arm in delta(above, there, course, forks[node], under):
                    lines.append(arm)
                    size = np.full(len(arm) - 1, carried[node])
                    courses.append(np.column_stack((arm[:-1], arm[1:], size * 0, size * 0, size, size)))
            if not river[after] or largest[after] != node:
                break
            node, above, here = after, here, there
        if len(controls) > 1:
            line = _smooth(np.array(controls))
            marks = np.arange(len(line)) / PIECES
            wide = np.interp(marks, np.arange(len(halves)), np.array(halves))
            size = np.interp(marks, np.arange(len(grown)), np.array(grown))
            lines.append(line)
            courses.append(np.column_stack((line[:-1], line[1:], wide[:-1], wide[1:], size[:-1], size[1:])))
    return tuple(lines), np.concatenate(courses) if courses else np.zeros((0, 8))


def _away(x: Floats, y: Floats, stretches: Floats, circumference_km: int) -> tuple[Floats, Floats]:
    """
    For every place and every stretch, how far the place lies from the stretch and at which part of it,
    0 at its first end and 1 at its second, the nearest point is.
    """
    east = x[:, None] - stretches[None, :, 0]
    east -= circumference_km * np.round(east / circumference_km)
    south = y[:, None] - stretches[None, :, 1]
    along_x, along_y = stretches[:, 2] - stretches[:, 0], stretches[:, 3] - stretches[:, 1]
    length = np.maximum(along_x**2 + along_y**2, SMALLEST)
    part = np.clip((east * along_x + south * along_y) / length, 0.0, 1.0)
    away: Floats = np.sqrt((east - part * along_x) ** 2 + (south - part * along_y) ** 2)
    return away, part


def _nests(stretches: Floats, reach: Floats, side: float, rows: int, around: int) -> dict[int, Indices]:
    """
    For every square of the skeleton a stretch comes within its reach of, the stretches that do.
    """
    found: dict[int, list[int]] = {}
    for number, (west, north, east, south) in enumerate(stretches[:, :4].tolist()):
        far = float(reach[number])
        low = math.floor((min(west, east) - far) / side)
        high = math.floor((max(west, east) + far) / side)
        top = max(math.floor((min(north, south) - far) / side), 0)
        bottom = min(math.floor((max(north, south) + far) / side), rows - 1)
        for row in range(top, bottom + 1):
            for column in range(low, high + 1):
                found.setdefault(row * around + column % around, []).append(number)
    return {square: np.array(near, dtype=np.int64) for square, near in found.items()}


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


def _around(grid: Floats, east: Floats, south: Floats) -> tuple[Floats, Floats, Floats, Floats, Floats, Floats]:
    """
    The four nodes around a place given in squares, and how far the place lies from the first of them
    to the east and to the south; x wraps, the poles hold their row.
    """
    rows, around = grid.shape
    east = east - 0.5
    south = np.clip(south - 0.5, 0.0, rows - 1.0)
    column = np.floor(east).astype(np.int64)
    row = np.minimum(np.floor(south).astype(np.int64), max(rows - 2, 0))
    below = np.minimum(row + 1, rows - 1)
    west, further = column % around, (column + 1) % around
    return grid[row, west], grid[row, further], grid[below, west], grid[below, further], east - column, south - row


def _between(grid: Floats, east: Floats, south: Floats) -> Floats:
    """
    A grid of nodes read between the four around a place given in squares.
    """
    first, second, third, fourth, along, down = _around(grid, east, south)
    read: Floats = (first * (1 - along) + second * along) * (1 - down) + (third * (1 - along) + fourth * along) * down
    return read


@dataclass(frozen=True)
class Rivers:
    """
    The rivers of a planet: the nodes that carry them, what every node carries, the lines, every stretch
    of them with its bed and its size, the filled surface and the nodes whose hollow holds a lake.
    """

    circumference_km: int
    nodes: Flags
    flow: Floats
    lines: tuple[Floats, ...]
    courses: Floats
    islands: float
    valley_km: float
    surface: Floats
    lakes: Flags

    @property
    def side(self) -> float:
        return self.circumference_km / int(self.surface.shape[1])

    def lake(self, x: Floats, y: Floats) -> Floats:
        """
        The level of the lake a place in kilometres may lie in: that of the lake nodes among the four around
        it, lowered to the sea level as the place draws near a node with no lake, so that water stays
        in its basin and its shore follows the land, not the squares.
        """
        levels = np.where(self.lakes, self.surface, -np.inf)
        highest = np.maximum.reduce(_around(levels, x / self.side, y / self.side)[:4])
        near = _between(self.lakes.astype(np.float64), x / self.side, y / self.side)
        held: Floats = np.where(near > 0, np.maximum(highest, 0.0) * near, -np.inf)
        return held

    @cached_property
    def beds(self) -> Floats:
        """
        The stretches that have a bed: their two ends and half the width at each.
        """
        return self.courses[(self.courses[:, 4] > 0) | (self.courses[:, 5] > 0)][:, :6]

    @cached_property
    def valleys(self) -> Floats:
        """
        Every stretch as its two ends and the size of the river at each.
        """
        return self.courses[:, [0, 1, 2, 3, 6, 7]]

    @cached_property
    def _bedded(self) -> dict[int, Indices]:
        rows, around = self.surface.shape
        return _nests(self.beds, self.beds[:, 4:].max(axis=1), self.side, rows, around)

    @cached_property
    def _valleyed(self) -> dict[int, Indices]:
        rows, around = self.surface.shape
        return _nests(self.valleys, np.full(len(self.valleys), self.valley_km), self.side, rows, around)

    def _read(self, x: Floats, y: Floats, stretches: Floats, nests: dict[int, Indices], valley: bool) -> Floats:
        """
        For places in kilometres, what the stretches near each make of it: 1 in a bed, or the size of the
        largest river felt there. A place is judged by itself alone; the squares only say which stretches to ask.
        """
        rows, around = self.surface.shape
        east, south = (grid.ravel() for grid in np.broadcast_arrays(x, y))
        read = np.zeros(east.size)
        if nests:
            column = np.floor(east / self.side).astype(np.int64) % around
            row = np.clip(np.floor(south / self.side).astype(np.int64), 0, rows - 1)
            squares = row * around + column
            order = np.argsort(squares, kind='stable')
            found, starts = np.unique(squares[order], return_index=True)
            stops = [*starts[1:].tolist(), east.size]
            for square, start, stop in zip(found.tolist(), starts.tolist(), stops, strict=True):
                if square not in nests:
                    continue
                places = order[start:stop]
                near = stretches[nests[square]]
                away, part = _away(east[places], south[places], near, self.circumference_km)
                held = near[:, 4] + (near[:, 5] - near[:, 4]) * part
                if valley:
                    read[places] = (held * np.clip(1.0 - away / self.valley_km, 0.0, 1.0)).max(axis=1)
                else:
                    read[places] = (away <= held).any(axis=1)
        shaped: Floats = read.reshape(np.broadcast(x, y).shape)
        return shaped

    def bed(self, x: Floats, y: Floats) -> Flags:
        """
        Which places in kilometres lie in the bed of a great river.
        """
        lying: Flags = self._read(x, y, self.beds, self._bedded, False) > 0
        return lying

    def wet(self, x: Floats, y: Floats) -> Floats:
        """
        The flow at a place in kilometres, 0 to 1: the size of the largest river near it, falling to nothing
        at valley_km from the line. It is a ribbon along every river, the wider the larger the river.
        """
        return self._read(x, y, self.valleys, self._valleyed, True)

    def restate(self, frame: Skeleton, x: Floats, y: Floats) -> dict[str, Floats]:
        """
        Every layer the rules of biomes read at places in kilometres: those of the skeleton with lakes and
        the beds of great rivers as water, and the flow. A share of a bed, its most broken ground, stays an island.
        """
        layers = frame.restate(x, y, self.lake(x, y))
        water = self.bed(x, y) & (layers['relief'] <= 1.0 - self.islands)
        layers['elevation'] = np.where(water, np.minimum(layers['elevation'], 0.0), layers['elevation'])
        return {**layers, 'flow': self.wet(x, y)}

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
    course: Mapping[str, float],
    rng: np.random.Generator,
    under: Under | None = None,
) -> Rivers:
    """
    The steps: rain, flow over filled hollows, gathering, rivers followed up to their sources, the lines.
    Water leaves the land and the inland seas alike: only the ocean keeps it.
    """
    open_sea = ocean(land, course['ocean'])
    surface = fill(heights, ~open_sea)
    targets = drain(surface, ~open_sea)
    flow = gather(surface, targets, rain)
    chosen = sources(pick(flow, surface, land, course['share']), flow, targets)
    great = pick(flow, surface, land, course['great']) & chosen
    # The size of a river at a node: 0 for the least of all river nodes, 1 for the one that carries the most.
    sizes = np.zeros(flow.shape)
    ranked = np.flatnonzero(chosen)[np.argsort(flow[chosen], kind='stable')]
    sizes.flat[ranked] = np.linspace(0.0, 1.0, ranked.size)
    lines, courses = trace(flow, targets, chosen, great, land, open_sea, sizes, circumference_km, course, rng, under)
    return Rivers(
        circumference_km=circumference_km,
        nodes=chosen,
        flow=flow,
        lines=lines,
        courses=courses,
        islands=course['islands'],
        valley_km=course['valley_km'],
        surface=surface,
        lakes=flooded(heights, surface, land, course['lakes']),
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
    course: tuple[tuple[str, float], ...],
) -> Rivers:
    """
    Kept in the process beside the skeleton they are traced on, never in the state of a game.
    course is every number of the section rivers but the effects, as pairs, so that it can be a key.
    """
    frame = skeleton(seed, circumference_km, skeleton_km, sea, elevation, relief, moisture, temperature)

    def under(x: Floats, y: Floats) -> Flags:
        south = np.clip(y, 0.0, circumference_km / 2)
        sunk: Flags = frame.layers.height(x, south, frame.sea_level, frame.brim, frame.span) < 0
        return sunk

    rng = stream(seed, STREAM)
    return lay(frame.elevation, frame.land, frame.rain, circumference_km, dict(course), rng, under)
