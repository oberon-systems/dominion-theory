"""
How a band decides: needs scored against what it knows, as docs/game/decisions.md states it.
"""

import math
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Any

from ..content import GOODS, Params
from . import commands, lore
from .band import (
    CAMP,
    DIRECTIONS,
    GATHER,
    MOVE,
    NOTHING,
    PASSABILITY,
    ROAM,
    STARVATION,
    THIRST,
    Action,
    Band,
    around,
    building,
    camp,
    census,
    gathering,
    held_days,
    kept,
    left,
    moving,
    perceived,
    ranging,
    roaming,
    room,
    sheltered,
    short,
)
from .cells import Place

HUNGER = 'hunger'
REST = 'rest'
SHELTER = 'shelter'
WANDER = 'wander'
THREAT = 'threat'
# The need a property of a cell answers, and the state that makes it whole.
NEEDS: dict[str, tuple[str, str]] = {'food': (HUNGER, STARVATION), 'water': (THIRST, THIRST)}
# What a band may still do under the intent of each proposal: docs/game/decisions.md, Under an intent.
NARROWED: dict[str, frozenset[str]] = {
    commands.GO: frozenset({MOVE, ROAM, GATHER, CAMP}),
    commands.STAY: frozenset({GATHER, CAMP}),
    commands.WINTER: frozenset({GATHER, CAMP}),
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
    the stores lack a day's ration and a member would die tonight without it.
    """
    named = census(params, band).stages
    found: dict[str, float] = {}
    for prop, (need, _) in NEEDS.items():
        days = held_days(params, band, prop)
        dying = days < 1.0 and any(
            not member.player and left(params, member, name, prop) <= 1.0 + NOTHING
            for member, name in zip(band.members, named, strict=True)
        )
        found[need] = 1.0 if dying else level(params, days)
    return found


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


def seen(params: Params, band: Band, at: Place, era: str) -> dict[str, Any] | None:
    """
    A known cell as the band sees it: its threat with the dread of what happened there and lowered by a winter
    camp built on it, and what a known shore beside it gives where that is more, since a band gathers from a
    shore it stands by; the cell of a band that ranges gives what its reach does.
    """
    cell = band.known.get(at)
    if cell is None:
        return None
    held = cell
    for shore in _shores(params, band, at, era):
        for prop in _fed(params, shore, era):
            if shore.get(prop, 0.0) > held.get(prop, 0.0):
                held = {**held, prop: shore[prop]}
    if at == band.place and ranging(band):
        held = _ranged(params, band, held, era)
    if at in band.dread:
        held = {**held, THREAT: perceived(band, at, cell.get(THREAT, 0.0))}
    if at == band.place and sheltered(band):
        held = {**held, THREAT: held.get(THREAT, 0.0) * params.units.band.winter_camp.threat}
    return held


def _reach(params: Params, band: Band) -> list[dict[str, Any]]:
    """
    The known cells within the reach of a winter camp around the band that it believes it can enter.
    """
    reach = params.units.band.winter_camp.reach
    return [band.known[at] for at in around(band.place, reach) if reachable(band, at)]


def _ranged(params: Params, band: Band, held: dict[str, Any], era: str) -> dict[str, Any]:
    """
    The band's own cell with the best food and water of its reach, a cell away worth afar of its own.
    """
    afar = params.units.band.winter_camp.afar
    for cell in _reach(params, band):
        for prop in _fed(params, cell, era):
            if cell.get(prop, 0.0) * afar > held.get(prop, 0.0):
                held = {**held, prop: cell[prop] * afar}
    return held


def _shores(params: Params, band: Band, at: Place, era: str) -> list[dict[str, Any]]:
    around = (band.known.get((at[0] + dx, at[1] + dy)) for dx, dy in DIRECTIONS.values())
    return [cell for cell in around if cell is not None and params.biomes[cell['biome']].eras[era].shore]


def _fed(params: Params, cell: dict[str, Any], era: str) -> set[str]:
    """
    The properties the resources a known cell lists are gathered by.
    """
    return {params.resources[name].land for name in _listed(params, cell, era)}


def _listed(params: Params, cell: dict[str, Any], era: str) -> tuple[str, ...]:
    listed: tuple[str, ...] = params.biomes[cell['biome']].eras[era].resources
    return listed


def gathers(params: Params, band: Band, at: Place, era: str) -> set[str]:
    """
    The resources a band standing on a known cell can gather: those of the cell and of the shores beside it, and
    of its reach while it ranges.
    """
    cell = band.known.get(at)
    found = set() if cell is None else set(_listed(params, cell, era))
    for shore in _shores(params, band, at, era):
        found.update(_listed(params, shore, era))
    if at == band.place and ranging(band):
        for near in _reach(params, band):
            found.update(_listed(params, near, era))
    return found


def here(params: Params, band: Band, wanted: dict[str, float], era: str) -> float:
    """
    What staying is worth: the cell the band stands on, its threat sharpened by unease.
    """
    own = seen(params, band, band.place, era)
    return worth(params, own, wanted, band.unease)[0] if own else 0.0


def wintering(params: Params, band: Band, era: str) -> float:
    """
    What a winter camp on the cell the band stands on is worth: staying with its reach, under the threat a built
    camp leaves.
    """
    own = seen(params, band, band.place, era)
    if own is None:
        return 0.0
    if not ranging(band):
        own = _ranged(params, band, own, era)
    if not sheltered(band):
        own = {**own, THREAT: own.get(THREAT, 0.0) * params.units.band.winter_camp.threat}
    return worth(params, own, needs(params, band), band.unease)[0]


def reachable(band: Band, at: Place) -> bool:
    """
    Whether the band believes a cell can be entered.
    """
    cell = band.known.get(at)
    return cell is not None and cell[PASSABILITY] > 0


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
    own = seen(params, band, band.place, era)
    staying = here(params, band, wanted, era)
    unknown = dict(rules.decisions.unknown)
    found: list[Scored] = []
    if allowed is None or CAMP in allowed:
        found.append(Scored(camp(), 0.0, REST))
    if own and (allowed is None or GATHER in allowed):
        found.extend(_gathered(params, band, own, gathers(params, band, band.place, era), wanted))
    if allowed is None or MOVE in allowed or ROAM in allowed:
        hungry = max(wanted.values()) >= rules.roaming.hunger
        enterable = {at for at in band.known if reachable(band, at)}
        moves: list[Scored] = []
        roams: list[Scored] = []
        for name, (dx, dy) in DIRECTIONS.items():
            target = band.x + dx, band.y + dy
            if target not in enterable or (towards is not None and name not in towards):
                continue
            if towards is not None:
                gain, need, source, kept, pace = weights.intent - staying, REST, None, 0.0, 1.0
            else:
                pull, need, source = _pull(params, band, era, (dx, dy), enterable, wanted, unknown)
                gain, kept = pull - staying, weights.momentum if band.target == target else 0.0
                pace = rules.roaming.speed
            moves.append(Scored(moving(name), weights.move * gain + kept, need, source))
            ahead = band.known[target]
            ahead_of = _worths(params, band, ahead, set(_listed(params, ahead, era)), wanted)
            short_of = [score for name, (score, *_) in ahead_of.items() if short(params, band, name)]
            on_the_way = rules.roaming.share * sum(short_of)
            roams.append(Scored(roaming(name), weights.move * gain * pace + kept + on_the_way, need, source))
        if (allowed is None or MOVE in allowed) and (walking or not hungry):
            found.extend(moves)
        if allowed is None or ROAM in allowed:
            found.extend(roams)
    return found


def _worths(
    params: Params, band: Band, own: dict[str, Any], listed: Collection[str], wanted: dict[str, float]
) -> dict[str, tuple[float, str, float]]:
    """
    What a gathering of every resource listed that the cell gives would be worth by the need it serves and the
    share that fits, with that need and its pull.
    """
    rules = params.units.band
    free = room(params, band)
    found: dict[str, tuple[float, str, float]] = {}
    for name, rate in rules.gathering.items():
        resource = params.resources[name]
        value = own.get(resource.land, 0.0)
        pulled = _pulled(params, band, name, wanted) if name in listed and value > 0 else None
        if pulled is not None:
            need, pull = pulled
            haul = census(params, band).gatherers * rate * value * resource.weight_kg
            fits = min(free / haul, 1.0) if haul > 0 else 0.0
            found[name] = pull * value * fits, need, pull
    return found


def _pulled(params: Params, band: Band, name: str, wanted: dict[str, float]) -> tuple[str, float] | None:
    """
    The need a resource serves and how hard it pulls the gatherers: hunger or thirst by their weight, or a good
    the band has learned to gather, by the share missing of its keep, while the band is not hungry.
    """
    rules = params.units.band
    weights = rules.decisions.weights
    resource = params.resources[name]
    if resource.property in NEEDS:
        need = NEEDS[resource.land][0]
        return need, getattr(weights, need) * wanted[need]
    hungry = max(wanted.values()) >= rules.roaming.hunger
    if resource.kind != GOODS or hungry or not lore.opened(params, band, lore.GATHERS, name):
        return None
    wants = kept(params, band, name)
    return (GOODS, weights.goods * max(0.0, 1.0 - band.held(name) / wants)) if wants > 0 else None


def split(pulls: dict[str, float]) -> dict[str, float]:
    """
    The share of the gatherers every resource gets: its pull over all of them; a pull of 0 gets nobody.
    """
    total = sum(pulls.values())
    return {} if total <= 0 else {name: round(pull / total, 9) for name, pull in pulls.items() if pull > 0}


def _gathered(
    params: Params, band: Band, own: dict[str, Any], listed: Collection[str], wanted: dict[str, float]
) -> list[Scored]:
    """
    One gathering of what the cell gives, the gatherers shared by need, worth the sum of every share of what
    its resource is worth; none when nothing is wanted.
    """
    worths = _worths(params, band, own, listed, wanted)
    shares = split({name: pull for name, (_, _, pull) in worths.items()})
    if not shares:
        return []
    score = sum(worths[name][0] * share for name, share in shares.items())
    loudest = max(shares, key=lambda name: worths[name][0] * shares[name])
    return [Scored(gathering(shares), score, worths[loudest][1])]


def _pull(
    params: Params,
    band: Band,
    era: str,
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
    candidates = [(at, seen(params, band, at, era)) for at in nearer]
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


def looks(params: Params, band: Band, era: str, at: Place) -> dict[str, Any] | None:
    """
    A cell as a route sees it: a known one the band believes it can enter, with its dread, or what it expects
    of land it does not know; None where it cannot step.
    """
    if at not in band.known:
        return dict(params.units.band.decisions.unknown)
    return seen(params, band, at, era) if reachable(band, at) else None


def intended(params: Params, band: Band, proposal: dict[str, Any], era: str, towards: str | None) -> Scored:
    """
    The best of what an intent leaves the band, a go narrowed to the direction of the next cell of its route;
    a winter camp is built before anything else unless the band starves or thirsts.
    """
    suffering = STARVATION in band.states or THIRST in band.states
    if proposal['kind'] == commands.WINTER and not sheltered(band) and not suffering:
        return Scored(building(), 0.0, SHELTER)
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
