"""
The band: what it holds and the rules of its day, as docs/units/band.md and docs/game/01_bands.md state them.
"""

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import numpy as np

from ..content import Band as Rules
from ..content import Params
from .cells import Place

KIND = 'band'
MOVE = 'move'
ROAM = 'roam'
GATHER = 'gather'
CAMP = 'camp'
NORMAL = 'normal'
STARVATION = 'starvation'
THIRST = 'thirst'
TIREDNESS = 'tiredness'
HUNGER = 'hunger'
ENCOUNTER = 'encounter'
AGE = 'age'
FRAILTY = 'frailty'
BIRTH = 'birth'
PASSABILITY = 'passability'
FEMALE = 'female'
MALE = 'male'
SEXES = (FEMALE, MALE)
PREGNANT = 'pregnant'
INJURED = 'injured'

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
class Member:
    age_days: int
    sex: str
    pregnant_until: int | None = None
    rest_until: int | None = None
    injured_until: int | None = None
    player: bool = False

    @classmethod
    def read(cls, plain: dict[str, Any]) -> Member:
        return cls(**plain)

    def plain(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Census:
    """
    What the members of a band add up to, kept until they change.
    """

    stages: tuple[str, ...]
    counts: dict[str, int]
    gatherers: float
    eaters: float
    carriers: float
    pace: float
    tires: float
    voters: int
    pregnant: int
    injured: int


@dataclass
class Band:
    id: int
    x: int
    y: int
    members: list[Member]
    stores: dict[str, list[list[float]]]
    fatigue: float = 0.0
    states: list[str] = field(default_factory=list)
    action: Action = field(default_factory=lambda: {'kind': CAMP})
    intent: dict[str, Any] | None = None
    known: dict[Place, dict[str, Any]] = field(default_factory=dict)
    progress: float = 0.0
    target: Place | None = None
    short: dict[str, int] = field(default_factory=dict)
    reason: dict[str, Any] | None = None
    wander: dict[str, Any] | None = None
    counted: tuple[int, Census] | None = field(default=None, init=False, repr=False, compare=False)

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
            members=[Member.read(member) for member in plain['members']],
            stores={name: [list(lot) for lot in lots] for name, lots in plain['stores'].items()},
            fatigue=plain['fatigue'],
            states=list(plain['states']),
            action=dict(plain['action']),
            intent=plain['intent'],
            known=known,
            progress=plain['progress'],
            target=None if target is None else (target[0], target[1]),
            short=dict(plain['short']),
            reason=plain['reason'],
            wander=plain['wander'],
        )

    @property
    def place(self) -> Place:
        return self.x, self.y

    @property
    def population(self) -> int:
        return len(self.members)

    def changed(self) -> None:
        """
        Forgets the census; called by whatever adds, removes, ages or hurts a member.
        """
        self.counted = None

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
            'members': [member.plain() for member in self.members],
            'stores': {name: [list(lot) for lot in lots] for name, lots in sorted(self.stores.items())},
            'fatigue': self.fatigue,
            'states': list(self.states),
            'action': dict(self.action),
            'intent': self.intent,
            'known': [{'x': x, 'y': y, **self.known[x, y]} for x, y in sorted(self.known)],
            'progress': self.progress,
            'target': None if self.target is None else list(self.target),
            'short': dict(sorted(self.short.items())),
            'reason': self.reason,
            'wander': self.wander,
        }

    def shown(self, params: Params, scale: int) -> dict[str, Any]:
        """
        The band as a client sees it: docs/game/01_bands.md, What the API shows.
        """
        counted = census(params, self)
        return {
            'id': self.id,
            'kind': KIND,
            'place': {'scale': scale, 'x': self.x, 'y': self.y},
            'population': self.population,
            'ages': dict(counted.counts),
            PREGNANT: counted.pregnant,
            INJURED: counted.injured,
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


def roaming(towards: str) -> Action:
    return {'kind': ROAM, 'towards': towards}


def start(land: Land, x: int, y: int, day: int, rng: np.random.Generator) -> Band:
    """
    The band of the start: members of random age inside the start stage and random sex, the first the player.
    """
    params = land.params
    rules = params.units.band
    low, high = bounds(params, rules.start.stage)
    count = rules.start.population
    ages = rng.integers(low, high, size=count)
    sexes = rng.integers(len(SEXES), size=count)
    members = [
        Member(int(age), SEXES[int(sex)], player=at == 0) for at, (age, sex) in enumerate(zip(ages, sexes, strict=True))
    ]
    stores = {name: [[float(day), float(amount)]] for name, amount in rules.start.stores.items() if amount > 0}
    band = Band(id=1, x=x, y=y, members=members, stores=stores)
    look(land, band, day)
    return band


def adults(count: int, age_days: int = 1000) -> list[Member]:
    """
    Members of one age, the sexes in turn, the first the player: a band whose people are all alike.
    """
    return [Member(age_days, SEXES[at % len(SEXES)], player=at == 0) for at in range(count)]


def bounds(params: Params, name: str) -> tuple[int, int]:
    """
    The ages in days a stage that ends spans, its last day excluded.
    """
    low = 0
    for held, stage in params.units.band.people.stages.items():
        if stage.until is None:
            break
        high = params.days(stage.until)
        if held == name:
            return low, high
        low = high
    raise KeyError(name)


def census(params: Params, band: Band) -> Census:
    """
    What the members add up to: gathering, eating and carrying summed by stage, pace and tiring as means.
    """
    if band.counted is not None and band.counted[0] == id(params):
        return band.counted[1]
    people = params.units.band.people
    stages = people.stages
    limits = [(name, math.inf if stage.until is None else params.days(stage.until)) for name, stage in stages.items()]
    named = tuple(next(name for name, until in limits if member.age_days < until) for member in band.members)
    injury = people.injury
    gatherers = eaters = carriers = pace = tires = 0.0
    voters = pregnant = injured = 0
    counts = dict.fromkeys(stages, 0)
    for member, name in zip(band.members, named, strict=True):
        stage = stages[name]
        hurt = member.injured_until is not None
        counts[name] += 1
        gatherers += stage.gathers * (injury.gathers if hurt else 1.0)
        eaters += stage.eats
        carriers += stage.carries
        pace += stage.pace * (injury.pace if hurt else 1.0)
        tires += stage.tires
        voters += stage.votes
        pregnant += member.pregnant_until is not None
        injured += hurt
    many = max(len(named), 1)
    counted = Census(named, counts, gatherers, eaters, carriers, pace / many, tires / many, voters, pregnant, injured)
    band.counted = id(params), counted
    return counted


def voters(params: Params, band: Band) -> int:
    return census(params, band).voters


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


def speed(params: Params, band: Band) -> float:
    rules = params.units.band
    pace = max(rules.speed.slowest, rules.speed.base - rules.speed.slowdown * band.population / 10)
    return pace * efficiency(rules, band) * census(params, band).pace


def efficiency(rules: Rules, band: Band) -> float:
    """
    The share of its pace and its gathering a band still has for its fatigue.
    """
    return 1.0 - rules.fatigue.slows * band.fatigue


def weight(params: Params, band: Band) -> float:
    return sum(band.held(name) * params.resources[name].weight_kg for name in band.stores)


def held_days(params: Params, band: Band, prop: str) -> float:
    """
    The days the stores of a property last the band; endless when nobody eats it.
    """
    resources = [name for name, held in params.resources.items() if held.property == prop]
    rates = params.units.band.consumption_per_day
    eaten = census(params, band).eaters * sum(rates.get(name, 0.0) for name in resources)
    return sum(band.held(name) for name in resources) / eaten if eaten > 0 else math.inf


def short(params: Params, band: Band, name: str) -> bool:
    """
    Whether the band holds fewer days of what a resource feeds than the top level of its needs asks.
    """
    top = max(level.days for level in params.units.band.decisions.levels.values())
    return held_days(params, band, params.resources[name].property) < top


def room(params: Params, band: Band) -> float:
    """
    The carrying weight still free, in kilos.
    """
    return max(census(params, band).carriers * params.units.band.carry_kg - weight(params, band), 0.0)


def act(land: Land, band: Band, action: Action, day: int) -> Action:
    """
    Carries one action out and gives it back as it was done: a move that cannot be made is a camp.
    """
    rules = land.params.units.band
    kind = action['kind']
    if kind == MOVE:
        done = _move(land, band, action, rules, 1.0)
    elif kind == ROAM:
        done = _roam(land, band, action, rules, day)
    elif kind == GATHER:
        done = _gather(land, band, action, rules, day)
    else:
        done = camp()
    if done['kind'] not in (MOVE, ROAM):
        band.progress, band.target = 0.0, None
    tired = getattr(rules.fatigue, done['kind'])
    if tired > 0:
        tired *= census(land.params, band).tires
    band.fatigue = min(max(band.fatigue + tired, 0.0), 1.0)
    band.action = done
    return done


def _move(land: Land, band: Band, action: Action, rules: Rules, pace: float) -> Action:
    dx, dy = DIRECTIONS[action['towards']]
    target = band.x + dx, band.y + dy
    if not enterable(land, *target):
        return camp()
    if band.target != target:
        band.progress, band.target = 0.0, target
    band.progress += speed(land.params, band) * pace * land.value(PASSABILITY, *target)
    if band.progress >= 1.0:
        band.x, band.y = target
        band.progress, band.target = 0.0, None
    return {'kind': action['kind'], 'towards': action['towards']}


def _roam(land: Land, band: Band, action: Action, rules: Rules, day: int) -> Action:
    """
    A share of a gathering tick of every resource the cell ahead gives that the band is short of, then a slow
    step into it.
    """
    dx, dy = DIRECTIONS[action['towards']]
    ahead = band.x + dx, band.y + dy
    if not enterable(land, *ahead):
        return camp()
    for name in rules.gathering:
        if name in _era(land, *ahead).resources and short(land.params, band, name):
            _take(land, band, name, rules, day, rules.roaming.share, ahead)
    return _move(land, band, action, rules, rules.roaming.speed)


def _gather(land: Land, band: Band, action: Action, rules: Rules, day: int) -> Action:
    name = action['resource']
    if name not in _era(land, band.x, band.y).resources:
        return camp()
    _take(land, band, name, rules, day, 1.0, band.place)
    return gathering(name)


def _take(land: Land, band: Band, name: str, rules: Rules, day: int, share: float, at: Place) -> None:
    params = land.params
    resource = params.resources[name]
    wanted = census(params, band).gatherers * rules.gathering.get(name, 0.0) * land.value(resource.property, *at)
    taken = min(wanted * share * efficiency(rules, band), room(params, band) / resource.weight_kg)
    if taken > 0:
        _stored(band, name, day, taken)
        capacity = params.eras[land.era].capacity.get(resource.property)
        if capacity and _era(land, *at).properties[resource.property].recovery is not None:
            land.deplete(*at, resource.property, taken / capacity)


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
    eaters = census(params, band).eaters
    for name, rate in params.units.band.consumption_per_day.items():
        need = left = eaters * rate
        lots = band.stores.get(name, [])
        for lot in lots:
            eaten = min(lot[1], left)
            lot[1] -= eaten
            left -= eaten
        band.stores[name] = [lot for lot in lots if lot[1] > 0]
        met[name] = 1.0 if need <= 0 else (need - left) / need
    return met


def suffer(
    params: Params, band: Band, met: dict[str, float], rng: np.random.Generator
) -> tuple[list[str], list[str], list[tuple[str, int]]]:
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
            weights = vulnerable(params, band, cause)
            dead = bury(band, _drawn(rng, weights, math.ceil(hardship.loss_per_day * sum(weights))))
            if dead:
                lost.append((cause, dead))
    return began, ended, lost


def vulnerable(params: Params, band: Band, cause: str) -> list[float]:
    """
    How much each member is exposed to a cause, by stage; the player never dies.
    """
    stages = params.units.band.people.stages
    named = census(params, band).stages
    return [
        0.0 if member.player else getattr(stages[name].dies, cause)
        for member, name in zip(band.members, named, strict=True)
    ]


def _drawn(rng: np.random.Generator, weights: list[float], count: int) -> list[int]:
    """
    The members a hazard takes, drawn by their weights without one twice; nothing is drawn when nobody is taken.
    """
    exposed = [at for at, held in enumerate(weights) if held > 0]
    count = min(count, len(exposed))
    if count <= 0:
        return []
    shares = np.array([weights[at] for at in exposed])
    picked = rng.choice(len(exposed), size=count, replace=False, p=shares / shares.sum())
    return sorted(exposed[int(at)] for at in picked)


def bury(band: Band, picked: list[int]) -> int:
    for at in sorted(picked, reverse=True):
        del band.members[at]
    if picked:
        band.changed()
    return len(picked)


def struck(
    params: Params, band: Band, taken: float, hurt: float, day: int, rng: np.random.Generator
) -> tuple[int, int]:
    """
    What an encounter does: the share taken of the people, weighed by how exposed they are, die, and the share
    hurt of those left is injured. Gives the dead and the injured.
    """
    weights = vulnerable(params, band, ENCOUNTER)
    dead = bury(band, _drawn(rng, weights, int(taken * sum(weights) + 0.5)))
    weights = _injurable(params, band)
    return dead, _injure(params, band, _drawn(rng, weights, int(hurt * sum(weights) + 0.5)), day)


def _injurable(params: Params, band: Band) -> list[float]:
    stages = params.units.band.people.stages
    named = census(params, band).stages
    return [
        0.0 if member.injured_until is not None else stages[name].dies.injury
        for member, name in zip(band.members, named, strict=True)
    ]


def _injure(params: Params, band: Band, picked: list[int], day: int) -> int:
    lasts = params.days(params.units.band.people.injury.lasts)
    for at in picked:
        band.members[at].injured_until = day + max(lasts, 1)
    if picked:
        band.changed()
    return len(picked)


def fed(params: Params, band: Band) -> bool:
    """
    Whether the band can feed more children: food in the stores for the days birth asks and no hunger or thirst.
    """
    if STARVATION in band.states or THIRST in band.states:
        return False
    return held_days(params, band, 'food') >= params.units.band.people.birth.days


@dataclass
class Lived:
    """
    What a day did to the members of a band.
    """

    lost: list[tuple[str, int]] = field(default_factory=list)
    born: int = 0
    injured: int = 0


def live(params: Params, band: Band, day: int, wellbeing: float, feeds: bool, rng: np.random.Generator) -> Lived:
    """
    The day of the members at its end: they age, die of age and frailty, heal or are hurt, give birth and conceive.
    """
    people = params.units.band.people
    per_year = params.time.days_per_year
    lived = Lived()
    for member in band.members:
        member.age_days += 1
        if member.injured_until is not None and member.injured_until <= day:
            member.injured_until = None
        if member.rest_until is not None and member.rest_until <= day:
            member.rest_until = None
    band.changed()
    begins, doubles = params.days(people.age.begins), params.days(people.age.doubles)
    old = [
        (
            0.0
            if member.player or member.age_days < begins
            else min(people.age.per_year * 2 ** ((member.age_days - begins) / doubles), 1.0) / per_year
        )
        for member in band.members
    ]
    lived.lost.append((AGE, bury(band, _chanced(rng, old))))
    frail = [held * (1.0 - wellbeing) / per_year for held in vulnerable(params, band, FRAILTY)]
    lived.lost.append((FRAILTY, bury(band, _chanced(rng, frail))))
    hurt = [held * people.injury.per_day for held in _injurable(params, band)]
    lived.injured = _injure(params, band, _chanced(rng, hurt), day)
    lived.born, mothers = _births(params, band, day, rng)
    lived.lost.append((BIRTH, bury(band, mothers)))
    if feeds:
        _conceive(params, band, day, rng)
    lived.lost = [(cause, count) for cause, count in lived.lost if count]
    return lived


def _chanced(rng: np.random.Generator, chances: list[float]) -> list[int]:
    """
    The members whose chance came up; one number is drawn for every member whatever its chance.
    """
    drawn = rng.random(len(chances))
    return [at for at, chance in enumerate(chances) if drawn[at] < chance]


def _births(params: Params, band: Band, day: int, rng: np.random.Generator) -> tuple[int, list[int]]:
    """
    The children born alive today and the mothers who died of it.
    """
    birth = params.units.band.people.birth
    low, high = params.days(birth.pause.min), params.days(birth.pause.max)
    born: list[Member] = []
    mothers: list[int] = []
    for at, member in enumerate(band.members):
        if member.pregnant_until is None or member.pregnant_until > day:
            continue
        lives, dies, sex, pause = rng.random(), rng.random(), rng.integers(len(SEXES)), rng.integers(low, high + 1)
        member.pregnant_until, member.rest_until = None, day + int(pause)
        if lives < birth.child_survives:
            born.append(Member(0, SEXES[int(sex)]))
        if dies < birth.mother_dies and not member.player:
            mothers.append(at)
    band.members.extend(born)
    band.changed()
    return len(born), mothers


def _conceive(params: Params, band: Band, day: int, rng: np.random.Generator) -> None:
    """
    Every woman of a stage that conceives, neither pregnant nor resting, may conceive while such a man lives.
    """
    people = params.units.band.people
    named = census(params, band).stages
    able = [people.stages[name].conceives for name in named]
    if not any(member.sex == MALE and can for member, can in zip(band.members, able, strict=True)):
        return
    drawn = rng.random(len(band.members))
    pregnancy = max(params.days(people.birth.pregnancy), 1)
    for at, (member, can) in enumerate(zip(band.members, able, strict=True)):
        ready = can and member.sex == FEMALE and member.pregnant_until is None and member.rest_until is None
        if ready and drawn[at] < people.birth.conceive_per_day:
            member.pregnant_until = day + pregnancy
    band.changed()
