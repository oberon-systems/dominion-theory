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
    ROAM,
    STARVATION,
    THIRST,
    Action,
    Band,
    camp,
    census,
    gathering,
    held_days,
    moving,
    perceived,
    roaming,
    room,
    short,
)
from .cells import Place

HUNGER = 'hunger'
REST = 'rest'
WANDER = 'wander'
THREAT = 'threat'
# The need a property of a cell answers, and the state that makes it whole.
NEEDS: dict[str, tuple[str, str]] = {'food': (HUNGER, STARVATION), 'water': (THIRST, THIRST)}
# What a band may still do under the intent of each proposal: docs/game/decisions.md, Under an intent.
NARROWED: dict[str, frozenset[str]] = {
    commands.MOVE: frozenset({MOVE, ROAM, CAMP}),
    commands.STAY: frozenset({GATHER, CAMP}),
}


@dataclass(frozen=True)
class Scored:
    action: Action
    score: float
    need: str
    pull: Place | None = None


def needs(params: Params, band: Band) -> dict[str, float]:
    """
    Hunger and thirst, each from 0, nothing wanted, to 1: the level of the days in the stores, or whole while
    the state holds.
    """
    return {
        need: 1.0 if state in band.states else level(params, held_days(params, band, prop))
        for prop, (need, state) in NEEDS.items()
    }


def level(params: Params, days: float) -> float:
    """
    The need of the first level, from the most days down, that the days in the stores reach; none when
    nobody eats it.
    """
    if math.isinf(days):
        return 0.0
    levels = sorted(params.units.band.decisions.levels.values(), key=lambda held: held.days, reverse=True)
    return next(held.need for held in levels if days >= held.days)


def calm(wanted: dict[str, float]) -> float:
    """
    How little hunger and thirst press: a calm band thinks of growth and fears danger.
    """
    return 1.0 - max(wanted[need] for need, _ in NEEDS.values())


def wellbeing(params: Params, band: Band, threat: float) -> float:
    """
    How well the band lives on its cell: the weighted mean of fed, watered, safe and rested.
    """
    weights = params.units.band.population.wellbeing
    wanted = needs(params, band)
    parts = (
        (weights.food, 1.0 - wanted[HUNGER]),
        (weights.water, 1.0 - wanted[THIRST]),
        (weights.safety, 1.0 - threat),
        (weights.rest, 1.0 - band.fatigue),
    )
    return sum(weight * part for weight, part in parts) / sum(weight for weight, _ in parts)


def seen(band: Band, at: Place) -> dict[str, Any] | None:
    """
    A known cell as the band sees it: its threat with the dread of what happened there.
    """
    cell = band.known.get(at)
    if cell is None or at not in band.dread:
        return cell
    return {**cell, THREAT: perceived(band, at, cell.get(THREAT, 0.0))}


def here(params: Params, band: Band, wanted: dict[str, float]) -> float:
    """
    What staying is worth: the cell the band stands on, its threat sharpened by unease.
    """
    own = seen(band, band.place)
    return worth(params, own, wanted, band.unease)[0] if own else 0.0


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


def worth(params: Params, cell: dict[str, Any], wanted: dict[str, float], unease: float = 0.0) -> tuple[float, str]:
    """
    How good it would be to stand on a known cell now, and the need that says so loudest; unease makes a calm
    band fear its threat more.
    """
    parts = {need: wanted[need] * cell.get(prop, 0.0) for prop, (need, _) in NEEDS.items()}
    loudest = max(parts, key=lambda need: parts[need])
    fear = params.units.band.decisions.weights.safety * calm(wanted) * (1.0 + unease) * cell.get(THREAT, 0.0)
    return sum(parts.values()) - fear, loudest


def _far(a: Place, b: Place) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def options(
    params: Params,
    band: Band,
    era: str,
    allowed: Collection[str] | None = None,
    towards: Collection[str] | None = None,
    walking: bool = False,
) -> list[Scored]:
    """
    Everything the band could do with its score, in the order that settles a tie: the camp, the gatherings,
    the moves clockwise from the north, the roams the same. An intent narrows the kinds and the directions and
    fixes the pull, not the pace; walking scores the moves of a hungry band too.
    """
    rules = params.units.band
    weights = rules.decisions.weights
    wanted = needs(params, band)
    own = band.known.get(band.place, {})
    staying = here(params, band, wanted)
    unknown = dict(rules.decisions.unknown)
    found: list[Scored] = []
    if allowed is None or CAMP in allowed:
        found.append(Scored(camp(), 0.0, REST))
    gathered = _gathered(params, band, own, era, wanted) if own else []
    if allowed is None or GATHER in allowed:
        found.extend(gathered)
    if allowed is None or MOVE in allowed or ROAM in allowed:
        hungry = max(wanted.values()) >= rules.roaming.hunger
        enterable = {at for at in band.known if reachable(params, band, at, era)}
        moves: list[Scored] = []
        roams: list[Scored] = []
        for name, (dx, dy) in DIRECTIONS.items():
            target = band.x + dx, band.y + dy
            if target not in enterable or (towards is not None and name not in towards):
                continue
            if towards is not None:
                gain, need, source, kept, pace = weights.intent - staying, REST, None, 0.0, 1.0
            else:
                pull, need, source = _pull(params, band, (dx, dy), enterable, wanted, unknown)
                gain, kept = pull - staying, weights.momentum if band.target == target else 0.0
                pace = rules.roaming.speed
            moves.append(Scored(moving(name), weights.move * gain + kept, need, source))
            ahead = _gathered(params, band, band.known[target], era, wanted)
            short_of = [held.score for held in ahead if short(params, band, held.action['resource'])]
            on_the_way = rules.roaming.share * sum(short_of)
            roams.append(Scored(roaming(name), weights.move * gain * pace + kept + on_the_way, need, source))
        if (allowed is None or MOVE in allowed) and (walking or not hungry):
            found.extend(moves)
        if allowed is None or ROAM in allowed:
            found.extend(roams)
    return found


def _gathered(params: Params, band: Band, own: dict[str, Any], era: str, wanted: dict[str, float]) -> list[Scored]:
    """
    A gathering of every resource the cell gives, scored by the need it serves and the share that fits.
    """
    rules = params.units.band
    free = room(params, band)
    listed = params.biomes[own['biome']].eras[era].resources
    found = []
    for name, rate in rules.gathering.items():
        resource = params.resources[name]
        if name in listed and resource.property in NEEDS:
            need = NEEDS[resource.property][0]
            value = own.get(resource.property, 0.0)
            haul = census(params, band).gatherers * rate * value * resource.weight_kg
            fits = min(free / haul, 1.0) if haul > 0 else 0.0
            score = getattr(rules.decisions.weights, need) * wanted[need] * value * fits
            found.append(Scored(gathering(name), score, need))
    return found


def _pull(
    params: Params,
    band: Band,
    step: Place,
    enterable: set[Place],
    wanted: dict[str, float],
    unknown: dict[str, float],
) -> tuple[float, str, Place]:
    """
    The best land that way: a known cell nearer that way than here, or the unknown `horizon` cells past what
    the band sees, which is worth what the band expects of land it does not know.
    """
    rules = params.units.band
    distance = rules.decisions.distance
    target = band.x + step[0], band.y + step[1]
    beyond = rules.sight + rules.decisions.horizon
    past = band.x + step[0] * beyond, band.y + step[1] * beyond
    nearer = [at for at in sorted(enterable) if at == target or _far(target, at) < _far(band.place, at)]
    candidates = [(at, seen(band, at)) for at in nearer]
    if rules.decisions.horizon and past not in band.known:
        candidates.append((past, unknown))
    best: tuple[float, str, Place] | None = None
    for at, cell in candidates:
        away = _far(band.place, at)
        value, need = worth(params, cell or {}, wanted, band.unease)
        # Distance makes good land less good and known bad land worse; the unknown is no worse for being far.
        if value > 0:
            value = value / (1.0 + away * distance)
        elif cell is not unknown:
            value = value * (1.0 + away * distance)
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


def intended(params: Params, band: Band, proposal: dict[str, Any], era: str) -> Scored | None:
    """
    The best of what an intent leaves the band; None when the way of a move is closed.
    """
    towards = None
    if proposal['kind'] == commands.MOVE:
        towards = way(params, band, proposal['towards'], era)
        if towards is None:
            return None
    found = options(params, band, era, NARROWED[proposal['kind']], None if towards is None else {towards})
    return max(found, key=lambda held: held.score)


def decide(
    params: Params,
    band: Band,
    day: int,
    era: str,
    pick: Callable[[int], int] | None = None,
) -> Action:
    """
    The action of a free band, with its reason kept on the band. pick(count) draws one of count,
    and is asked only when the band starts to wander.
    """
    scored = options(params, band, era)
    best = max(scored, key=lambda held: held.score)
    if best.score > params.units.band.decisions.idle:
        band.wander = None
        band.reason = reason(best)
        return best.action
    moves = [held.action['towards'] for held in scored if held.action['kind'] == ROAM]
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
    band.reason = {'action': ROAM, 'towards': towards, 'need': WANDER, 'score': best.score, 'pull': None}
    return roaming(towards)


def reason(held: Scored) -> dict[str, Any]:
    told = {name: value for name, value in held.action.items() if name != 'kind'}
    pull = None if held.pull is None else {'x': held.pull[0], 'y': held.pull[1]}
    return {'action': held.action['kind'], **told, 'need': held.need, 'score': held.score, 'pull': pull}
