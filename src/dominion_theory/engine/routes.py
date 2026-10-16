"""
The way a band lays to a place it was sent to: the cheapest cells as it sees them, as docs/game/decisions.md
states it.
"""

import heapq
import math
from collections.abc import Callable
from typing import Any

from ..content import Params
from .band import DIRECTIONS, PASSABILITY, Band
from .cells import Place

FOOD = 'food'
WATER = 'water'
THREAT = 'threat'


def cost(params: Params, cell: dict[str, Any], wanted: dict[str, float], done: float = 0.0) -> float:
    """
    What a step into a cell costs: the time its passability takes but for the share already walked, its
    threat, and the food and water it lacks as much as the band wants them.
    """
    weights = params.units.band.route
    lacks = weights.hunger * wanted['hunger'] * (1.0 - cell.get(FOOD, 0.0))
    lacks += weights.thirst * wanted['thirst'] * (1.0 - cell.get(WATER, 0.0))
    return float((1.0 - done) / cell[PASSABILITY] + weights.threat * cell.get(THREAT, 0.0) + lacks)


def lay(
    params: Params,
    band: Band,
    to: Place,
    inside: Callable[[int, int], bool],
    looks: Callable[[Place], dict[str, Any] | None],
    wanted: dict[str, float],
) -> list[Place] | None:
    """
    The cells from the next one to `to`, by eight neighbours within a box around the band and the target;
    looks(at) gives a cell as the band sees it, or None where it cannot step. None when there is no way. The
    cell the band is partway into costs only the rest of its step, so a way laid anew keeps it.
    """
    margin = params.units.band.route.margin
    left, right = min(band.x, to[0]) - margin, max(band.x, to[0]) + margin
    top, bottom = min(band.y, to[1]) - margin, max(band.y, to[1]) + margin
    start = band.place
    spent: dict[Place, float] = {start: 0.0}
    came: dict[Place, Place] = {}
    queue: list[tuple[float, int, int, Place]] = [(0.0, 0, 0, start)]
    pushed = 0
    while queue:
        held, _, _, at = heapq.heappop(queue)
        if at == to:
            break
        if held > spent[at]:
            continue
        for dx, dy in DIRECTIONS.values():
            step = at[0] + dx, at[1] + dy
            if not (left <= step[0] <= right and top <= step[1] <= bottom and inside(*step)):
                continue
            cell = looks(step)
            if cell is None:
                continue
            done = band.progress if at == start and step == band.target else 0.0
            total = held + cost(params, cell, wanted, done)
            if total < spent.get(step, float('inf')):
                spent[step], came[step] = total, at
                pushed += 1
                # Of two ways that cost the same, the one nearer the straight line to the target.
                straight = (to[0] - step[0]) ** 2 + (to[1] - step[1]) ** 2
                heapq.heappush(queue, (total, straight, pushed, step))
    if to not in came:
        return None
    way = [to]
    while way[-1] in came and came[way[-1]] != start:
        way.append(came[way[-1]])
    return way[::-1]


def towards(at: Place, to: Place) -> str:
    """
    The one of the eight directions closest to the way from one cell to another.
    """
    way = to[0] - at[0], to[1] - at[1]
    return max(DIRECTIONS, key=lambda name: _cosine(DIRECTIONS[name], way))


def _cosine(a: Place, b: Place) -> float:
    return (a[0] * b[0] + a[1] * b[1]) / (math.hypot(*a) * math.hypot(*b))
