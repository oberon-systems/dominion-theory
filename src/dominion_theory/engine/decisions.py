"""
How a band decides: needs scored against what it knows, as docs/game/decisions.md states it.
"""

import math
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any

from ..content import Params
from . import commands
from .band import (
    CAMP,
    DIRECTIONS,
    GATHER,
    MOVE,
    PASSABILITY,
    STARVATION,
    THIRST,
    TIREDNESS,
    Action,
    Band,
    camp,
    gathering,
    moving,
    room,
)
from .cells import Place

HUNGER = 'hunger'
REST = 'rest'
WANDER = 'wander'
# The need a property of a cell answers, and the state that doubles it.
NEEDS: dict[str, tuple[str, str]] = {'food': (HUNGER, STARVATION), 'water': (THIRST, THIRST)}
EFFORT = 4.0
# What a band may still do under the intent of each proposal: docs/game/decisions.md, Under an intent.
NARROWED: dict[str, frozenset[str]] = {
    commands.MOVE: frozenset({MOVE, CAMP}),
    commands.REST: frozenset({CAMP}),
    commands.STAY: frozenset({GATHER, CAMP}),
}


@dataclass(frozen=True)
class Scored:
    action: Action
    score: float
    need: str
    pull: Place | None = None


def needs(params: Params, band: Band, part: str) -> dict[str, float]:
    """
    Hunger, thirst and rest, each from 0, nothing wanted, to 1.
    """
    rules = params.units.band
    comfort = params.parts(rules.decisions.comfort) / params.time.parts_per_day
    found: dict[str, float] = {}
    for prop, (need, state) in NEEDS.items():
        days = min(held_days(params, band, prop), comfort)
        wanted = 1.0 - days / comfort if comfort > 0 else 0.0
        found[need] = _held(wanted * (2.0 if state in band.states else 1.0))
    rest = band.fatigue + (rules.decisions.night if part in rules.decisions.night_parts else 0.0)
    found[REST] = _held(rest * (2.0 if TIREDNESS in band.states else 1.0))
    return found


def held_days(params: Params, band: Band, prop: str) -> float:
    """
    The days the stores of a property last the band; endless when nobody eats it.
    """
    resources = [name for name, held in params.resources.items() if held.property == prop]
    eaten = band.population * sum(params.units.band.consumption_per_day.get(name, 0.0) for name in resources)
    return sum(band.held(name) for name in resources) / eaten if eaten > 0 else math.inf


def _held(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def reachable(params: Params, band: Band, at: Place, era: str) -> bool:
    """
    Whether the band believes a cell can be entered: a shore only beside land it knows.
    """
    cell = band.known.get(at)
    if cell is None or cell[PASSABILITY] <= 0:
        return False
    if not params.biomes[cell['biome']].eras[era].shore:
        return True
    around = (band.known.get((at[0] + dx, at[1] + dy)) for dx, dy in DIRECTIONS.values())
    eras = (params.biomes[seen['biome']].eras[era] for seen in around if seen is not None)
    return any(not held.shore and held.properties[PASSABILITY].base > 0 for held in eras)


def worth(params: Params, cell: dict[str, Any], wanted: dict[str, float]) -> tuple[float, str]:
    """
    How good it would be to stand on a known cell now, and the need that says so loudest.
    """
    parts = {need: wanted[need] * cell.get(prop, 0.0) for prop, (need, _) in NEEDS.items()}
    loudest = max(parts, key=lambda need: parts[need])
    return sum(parts.values()) - params.units.band.decisions.weights.safety * cell.get('threat', 0.0), loudest


def _far(a: Place, b: Place) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def options(
    params: Params,
    band: Band,
    part: str,
    era: str,
    allowed: Collection[str] | None = None,
    towards: Collection[str] | None = None,
) -> list[Scored]:
    """
    Everything the band could do with its score, in the order that settles a tie: the camp, the gatherings,
    the moves clockwise from the north. An intent narrows the kinds and the directions and fixes the pull.
    """
    rules = params.units.band
    weights = rules.decisions.weights
    wanted = needs(params, band, part)
    own = band.known.get(band.place, {})
    here, _ = worth(params, own, wanted) if own else (0.0, REST)
    found: list[Scored] = []
    if allowed is None or CAMP in allowed:
        found.append(Scored(camp(), weights.rest * wanted[REST], REST))
    if own and (allowed is None or GATHER in allowed):
        free = room(params, band)
        listed = params.biomes[own['biome']].eras[era].resources
        for name, rate in rules.gathering.items():
            resource = params.resources[name]
            if name in listed and resource.property in NEEDS:
                need = NEEDS[resource.property][0]
                value = own.get(resource.property, 0.0)
                haul = band.population * rate * value * resource.weight_kg
                fits = min(free / haul, 1.0) if haul > 0 else 0.0
                found.append(Scored(gathering(name), getattr(weights, need) * wanted[need] * value * fits, need))
    if allowed is None or MOVE in allowed:
        enterable = {at for at in band.known if reachable(params, band, at, era)}
        for name, (dx, dy) in DIRECTIONS.items():
            target = band.x + dx, band.y + dy
            if target not in enterable or (towards is not None and name not in towards):
                continue
            effort = min(1.0 / band.known[target][PASSABILITY], EFFORT)
            tired = weights.rest * wanted[REST] * effort
            if towards is not None:
                found.append(Scored(moving(name), weights.move * (weights.intent - here) - tired, REST))
                continue
            pull, need, source = _pull(params, band, target, enterable, wanted)
            score = weights.move * (pull - here) - tired
            if band.target == target:
                score += weights.momentum
            found.append(Scored(moving(name), score, need, source))
    return found


def _pull(
    params: Params, band: Band, target: Place, enterable: set[Place], wanted: dict[str, float]
) -> tuple[float, str, Place]:
    distance = params.units.band.decisions.distance
    best: tuple[float, str, Place] | None = None
    for at in sorted(enterable):
        away = _far(band.place, at)
        if at == target or _far(target, at) < away:
            value, need = worth(params, band.known[at], wanted)
            # Distance makes good land less good and bad land worse.
            value = value / (1.0 + away * distance) if value > 0 else value * (1.0 + away * distance)
            if best is None or value > best[0]:
                best = value, need, at
    return best or (0.0, REST, target)


def beside(towards: str) -> tuple[str, str]:
    """
    The two directions next to one, the clockwise one first.
    """
    names = list(DIRECTIONS)
    at = names.index(towards)
    return names[(at + 1) % len(names)], names[(at - 1) % len(names)]


def way(params: Params, band: Band, towards: str, era: str) -> str | None:
    """
    The direction a band sent somewhere takes: that one, else one beside it, as far as the band knows.
    """
    for name in (towards, *beside(towards)):
        dx, dy = DIRECTIONS[name]
        if reachable(params, band, (band.x + dx, band.y + dy), era):
            return name
    return None


def intended(params: Params, band: Band, proposal: dict[str, Any], part: str, era: str) -> Scored | None:
    """
    The best of what an intent leaves the band; None when the way of a move is closed.
    """
    towards = None
    if proposal['kind'] == commands.MOVE:
        towards = way(params, band, proposal['towards'], era)
        if towards is None:
            return None
    found = options(params, band, part, era, NARROWED[proposal['kind']], None if towards is None else {towards})
    return max(found, key=lambda held: held.score)


def decide(
    params: Params,
    band: Band,
    part: str,
    day: int,
    era: str,
    pick: Callable[[int], int] | None = None,
) -> Action:
    """
    The action of a free band, with its reason kept on the band. pick(count) draws one of count,
    and is asked only when the band starts to wander.
    """
    scored = options(params, band, part, era)
    best = max(scored, key=lambda held: held.score)
    if best.score > params.units.band.decisions.idle:
        band.wander = None
        band.reason = reason(best)
        return best.action
    moves = [held.action['towards'] for held in scored if held.action['kind'] == MOVE]
    kept = band.wander
    if kept is not None and kept['until'] > day and kept['towards'] in moves:
        towards = kept['towards']
    elif moves and pick is not None:
        towards = moves[pick(len(moves))]
        length = params.parts(params.units.band.decisions.wander) // params.time.parts_per_day
        band.wander = {'towards': towards, 'until': day + max(length, 1)}
    else:
        band.wander = None
        band.reason = reason(best)
        return best.action
    band.reason = {'action': MOVE, 'towards': towards, 'need': WANDER, 'score': best.score, 'pull': None}
    return moving(towards)


def reason(held: Scored) -> dict[str, Any]:
    told = {name: value for name, value in held.action.items() if name != 'kind'}
    pull = None if held.pull is None else {'x': held.pull[0], 'y': held.pull[1]}
    return {'action': held.action['kind'], **told, 'need': held.need, 'score': held.score, 'pull': pull}
