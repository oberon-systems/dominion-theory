"""
The band: what it holds and the rules of its day, as docs/units/band.md and docs/game/01_bands.md state them.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..content import Band as Rules
from ..content import Params
from .cells import Place

KIND = 'band'
MOVE = 'move'
GATHER = 'gather'
CAMP = 'camp'
NORMAL = 'normal'
STARVATION = 'starvation'
THIRST = 'thirst'
TIREDNESS = 'tiredness'
HUNGER = 'hunger'
ENCOUNTER = 'encounter'
PASSABILITY = 'passability'

# Clockwise from the north; y grows to the south.
DIRECTIONS: dict[str, Place] = {
    'north': (0, -1),
    'north-east': (1, -1),
    'east': (1, 0),
    'south-east': (1, 1),
    'south': (0, 1),
    'south-west': (-1, 1),
    'west': (-1, 0),
    'north-west': (-1, -1),
}
# The state a shortage brings and the cause of death it is, by the property a resource is gathered by.
SHORTAGES: dict[str, tuple[str, str]] = {'food': (STARVATION, HUNGER), 'water': (THIRST, THIRST)}
STATES = (STARVATION, THIRST, TIREDNESS)
COLUMNS = ('id', 'x', 'y', 'state', 'action', 'people', 'food', 'water')

type Action = dict[str, Any]


class Land(Protocol):
    """
    What a band asks of the game it lives in.
    """

    params: Params
    era: str

    def inside(self, x: int, y: int) -> bool: ...

    def biome(self, x: int, y: int) -> str: ...

    def river(self, x: int, y: int) -> bool: ...

    def value(self, name: str, x: int, y: int) -> float: ...

    def deplete(self, x: int, y: int, name: str, amount: float) -> None: ...


@dataclass
class Band:
    id: int
    x: int
    y: int
    population: int
    stores: dict[str, list[list[float]]]
    fatigue: float = 0.0
    states: list[str] = field(default_factory=list)
    action: Action = field(default_factory=lambda: {'kind': CAMP})
    intent: dict[str, Any] | None = None
    known: dict[Place, dict[str, Any]] = field(default_factory=dict)
    births: float = 0.0
    progress: float = 0.0
    target: Place | None = None
    short: dict[str, int] = field(default_factory=dict)
    camped: int = 0
    reason: dict[str, Any] | None = None
    wander: dict[str, Any] | None = None

    @classmethod
    def read(cls, plain: dict[str, Any]) -> Band:
        known = {
            (cell['x'], cell['y']): {name: held for name, held in cell.items() if name not in ('x', 'y')}
            for cell in plain['known']
        }
        target = plain['target']
        return cls(
            id=plain['id'],
            x=plain['x'],
            y=plain['y'],
            population=plain['population'],
            stores={name: [list(lot) for lot in lots] for name, lots in plain['stores'].items()},
            fatigue=plain['fatigue'],
            states=list(plain['states']),
            action=dict(plain['action']),
            intent=plain['intent'],
            known=known,
            births=plain['births'],
            progress=plain['progress'],
            target=None if target is None else (target[0], target[1]),
            short=dict(plain['short']),
            camped=plain['camped'],
            reason=plain['reason'],
            wander=plain['wander'],
        )

    @property
    def place(self) -> Place:
        return self.x, self.y

    def held(self, resource: str) -> float:
        return sum(amount for _, amount in self.stores.get(resource, ()))

    def plain(self) -> dict[str, Any]:
        """
        All of the band, for the snapshot and the hash.
        """
        return {
            'id': self.id,
            'kind': KIND,
            'x': self.x,
            'y': self.y,
            'population': self.population,
            'stores': {name: [list(lot) for lot in lots] for name, lots in sorted(self.stores.items())},
            'fatigue': self.fatigue,
            'states': list(self.states),
            'action': dict(self.action),
            'intent': self.intent,
            'known': [{'x': x, 'y': y, **self.known[x, y]} for x, y in sorted(self.known)],
            'births': self.births,
            'progress': self.progress,
            'target': None if self.target is None else list(self.target),
            'short': dict(sorted(self.short.items())),
            'camped': self.camped,
            'reason': self.reason,
            'wander': self.wander,
        }

    def shown(self, scale: int) -> dict[str, Any]:
        """
        The band as a client sees it: docs/game/01_bands.md, What the API shows.
        """
        return {
            'id': self.id,
            'kind': KIND,
            'place': {'scale': scale, 'x': self.x, 'y': self.y},
            'population': self.population,
            'stores': {name: self.held(name) for name in sorted(self.stores)},
            'fatigue': self.fatigue,
            'states': list(self.states),
            'action': dict(self.action),
            'intent': self.intent,
            'reason': self.reason,
        }

    def row(self, params: Params) -> list[Any]:
        totals = dict.fromkeys(SHORTAGES, 0.0)
        for name in self.stores:
            prop = params.resources[name].property
            if prop in totals:
                totals[prop] += self.held(name)
        state = '+'.join(self.states) or NORMAL
        return [self.id, self.x, self.y, state, self.action['kind'], self.population, totals['food'], totals['water']]


def camp() -> Action:
    return {'kind': CAMP}


def gathering(resource: str) -> Action:
    return {'kind': GATHER, 'resource': resource}


def moving(towards: str) -> Action:
    return {'kind': MOVE, 'towards': towards}


def start(land: Land, x: int, y: int, day: int) -> Band:
    rules = land.params.units.band
    stores = {name: [[float(day), float(amount)]] for name, amount in rules.start.stores.items() if amount > 0}
    band = Band(id=1, x=x, y=y, population=rules.start.population, stores=stores)
    look(land, band, day)
    return band


def enterable(land: Land, x: int, y: int) -> bool:
    """
    A cell of the window that can be walked into now; a shore only where it touches land.
    """
    if not land.inside(x, y) or land.value(PASSABILITY, x, y) <= 0:
        return False
    return not _shore(land, x, y) or any(_is_land(land, x + dx, y + dy) for dx, dy in DIRECTIONS.values())


def _era(land: Land, x: int, y: int) -> Any:
    return land.params.biomes[land.biome(x, y)].eras[land.era]


def _shore(land: Land, x: int, y: int) -> bool:
    shore: bool = _era(land, x, y).shore
    return shore


def _is_land(land: Land, x: int, y: int) -> bool:
    if not land.inside(x, y) or _shore(land, x, y):
        return False
    base: float = _era(land, x, y).properties[PASSABILITY].base
    return base > 0


def speed(rules: Rules, band: Band) -> float:
    pace = max(rules.speed.slowest, rules.speed.base - rules.speed.slowdown * band.population / 10)
    return pace * _slowed(rules, band)


def _slowed(rules: Rules, band: Band) -> float:
    return rules.states.tiredness.slows if TIREDNESS in band.states else 1.0


def weight(params: Params, band: Band) -> float:
    return sum(band.held(name) * params.resources[name].weight_kg for name in band.stores)


def room(params: Params, band: Band) -> float:
    """
    The carrying weight still free, in kilos.
    """
    return max(band.population * params.units.band.carry_kg - weight(params, band), 0.0)


def act(land: Land, band: Band, action: Action, day: int) -> Action:
    """
    Carries one action out and gives it back as it was done: a move that cannot be made is a camp.
    """
    rules = land.params.units.band
    kind = action['kind']
    if kind == MOVE:
        done = _move(land, band, action, rules)
    elif kind == GATHER:
        done = _gather(land, band, action, rules, day)
    else:
        done = camp()
    if done['kind'] != MOVE:
        band.progress, band.target = 0.0, None
    if done['kind'] == CAMP:
        band.camped += 1
    tired = getattr(rules.fatigue, done['kind'])
    band.fatigue = min(max(band.fatigue + tired, 0.0), 1.0)
    band.action = done
    return done


def _move(land: Land, band: Band, action: Action, rules: Rules) -> Action:
    dx, dy = DIRECTIONS[action['towards']]
    target = band.x + dx, band.y + dy
    if not enterable(land, *target):
        return camp()
    if band.target != target:
        band.progress, band.target = 0.0, target
    band.progress += speed(rules, band) * land.value(PASSABILITY, *target)
    if band.progress >= 1.0:
        band.x, band.y = target
        band.progress, band.target = 0.0, None
    return moving(action['towards'])


def _gather(land: Land, band: Band, action: Action, rules: Rules, day: int) -> Action:
    params = land.params
    name = action['resource']
    if name not in _era(land, band.x, band.y).resources:
        return camp()
    resource = params.resources[name]
    wanted = band.population * rules.gathering.get(name, 0.0) * land.value(resource.property, band.x, band.y)
    taken = min(wanted * _slowed(rules, band), room(params, band) / resource.weight_kg)
    if taken > 0:
        _stored(band, name, day, taken)
        capacity = params.eras[land.era].capacity.get(resource.property)
        if capacity and _era(land, band.x, band.y).properties[resource.property].recovery is not None:
            land.deplete(band.x, band.y, resource.property, taken / capacity)
    return gathering(name)


def _stored(band: Band, name: str, day: int, amount: float) -> None:
    lots = band.stores.setdefault(name, [])
    if lots and lots[-1][0] == day:
        lots[-1][1] += amount
    else:
        lots.append([float(day), amount])


def tire(rules: Rules, band: Band) -> tuple[list[str], list[str]]:
    """
    Tiredness by the fatigue of the band: the states that began and those that ended.
    """
    tiredness = rules.states.tiredness
    if TIREDNESS not in band.states and band.fatigue >= tiredness.begins:
        return _begin(band, TIREDNESS), []
    if TIREDNESS in band.states and band.fatigue <= tiredness.ends:
        band.states.remove(TIREDNESS)
        return [], [TIREDNESS]
    return [], []


def _begin(band: Band, state: str) -> list[str]:
    band.states = [held for held in STATES if held in band.states or held == state]
    return [state]


def look(land: Land, band: Band, day: int) -> list[Place]:
    """
    Stores what the band sees around it and drops what it saw too long ago; gives the cells that are news.
    """
    params = land.params
    rules = params.units.band
    names = params.eras[land.era].properties
    news: list[Place] = []
    for y in range(band.y - rules.sight, band.y + rules.sight + 1):
        for x in range(band.x - rules.sight, band.x + rules.sight + 1):
            if not land.inside(x, y):
                continue
            seen: dict[str, Any] = {'biome': land.biome(x, y), 'river': land.river(x, y)}
            seen.update({name: land.value(name, x, y) for name in names})
            before = band.known.get((x, y))
            if before is None or any(before[name] != value for name, value in seen.items()):
                news.append((x, y))
            band.known[x, y] = {**seen, 'seen': day}
    oldest = day - params.parts(rules.memory) // params.time.parts_per_day
    for at in [at for at, cell in band.known.items() if cell['seen'] < oldest]:
        del band.known[at]
    return news


def spoil(params: Params, band: Band, day: int) -> None:
    per_day = params.time.parts_per_day
    for name in list(band.stores):
        keeps = params.parts(params.resources[name].spoils) // per_day
        band.stores[name] = [lot for lot in band.stores[name] if lot[0] + keeps > day]


def eat(params: Params, band: Band) -> dict[str, float]:
    """
    The people eat and drink for a day, the oldest lots first; gives the share of each need that was met.
    """
    met: dict[str, float] = {}
    for name, rate in params.units.band.consumption_per_day.items():
        need = left = band.population * rate
        lots = band.stores.get(name, [])
        for lot in lots:
            eaten = min(lot[1], left)
            lot[1] -= eaten
            left -= eaten
        band.stores[name] = [lot for lot in lots if lot[1] > 0]
        met[name] = 1.0 if need <= 0 else (need - left) / need
    return met


def suffer(params: Params, band: Band, met: dict[str, float]) -> tuple[list[str], list[str], list[tuple[str, int]]]:
    """
    What a day of eating did: the states that began, those that ended, and the people lost by cause.
    """
    rules = params.units.band
    per_day = params.time.parts_per_day
    worst: dict[str, float] = {}
    for name, share in met.items():
        prop = params.resources[name].property
        if prop in SHORTAGES:
            worst[prop] = min(worst.get(prop, 1.0), share)
    began: list[str] = []
    ended: list[str] = []
    lost: list[tuple[str, int]] = []
    for prop, share in worst.items():
        state, cause = SHORTAGES[prop]
        hardship = getattr(rules.states, state)
        band.short[prop] = band.short.get(prop, 0) + 1 if share < rules.states.short else 0
        if state in band.states and share >= 1.0:
            band.states.remove(state)
            ended.append(state)
        elif state not in band.states and band.short[prop] * per_day >= max(params.parts(hardship.after), 1):
            began.extend(_begin(band, state))
        if state in band.states:
            dead = min(math.ceil(band.population * hardship.loss_per_day), band.population)
            if dead:
                band.population -= dead
                lost.append((cause, dead))
    return began, ended, lost


def grow(params: Params, band: Band) -> int:
    """
    The births of a day: none in hunger or thirst, more after a day spent in camp.
    """
    rules = params.units.band.population
    rested = band.camped >= params.time.parts_per_day
    band.camped = 0
    if STARVATION in band.states or THIRST in band.states:
        return 0
    pace = rules.growth_per_year / params.time.days_per_year * (rules.rest_growth if rested else 1.0)
    band.births += band.population * pace
    born = int(band.births)
    band.births -= born
    band.population += born
    return born
