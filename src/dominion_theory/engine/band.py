"""
The band: what it holds and the rules of its day, as docs/units/band.md and docs/game/01_bands.md state them.
"""

import copy
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import numpy as np

from ..content import GOODS, KINDS, PERSONAL, TO, USES, Bonus, Duration, Params, Resource
from ..content import Band as Rules
from . import lore as lores
from .cells import Place
from .commands import WINTER
from .stock import Stock
from .streams import Streams

KIND = 'band'
MOVE = 'move'
ROAM = 'roam'
GATHER = 'gather'
CAMP = 'camp'
BUILD = 'build'
# The actions of a band that stands by its camp: guarded and sheltered as in camp, though it works around it.
STANDING = (CAMP, BUILD, GATHER)
NORMAL = 'normal'
STARVATION = 'starvation'
THIRST = 'thirst'
TIREDNESS = 'tiredness'
HUNGER = 'hunger'
ENCOUNTER = 'encounter'
AGE = 'age'
FRAILTY = 'frailty'
INJURY = 'injury'
BIRTH = 'birth'
PASSABILITY = 'passability'
FEMALE = 'female'
MALE = 'male'
SEXES = (FEMALE, MALE)
PREGNANT = 'pregnant'
INJURED = 'injured'
WOUNDS = 'wounds'
HUNTER = 'hunter'
ADULT = 'adult'
PULLER = 'puller'
NANNY = 'nanny'
FOOD, WATER = KINDS[:2]
EATEN, NIGHTS, ATTACKS, CURES, PULLED, HUNTS, CARRIED = USES
TO_BAND, TO_MEMBER = TO
CARRY_KG = 'units.band.carry_kg'
SICK = 'sick'
KIT = 'kit'
GAME = 'game'
MEAT = 'meat'
HEALS = 'heals'
CARRIES = 'carries'
HIDES = 'hides'

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
# The field of a member that keeps the days it went without, by the property.
DEFICITS: dict[str, str] = {'food': 'hungry', 'water': 'thirsty'}
# What is left of a reserve below this is nothing: the steps of a float are not a day.
NOTHING = 1e-9
STATES = (STARVATION, THIRST, TIREDNESS)
COLUMNS = ('id', 'x', 'y', 'state', 'action', 'people', 'food', 'water')

type Action = dict[str, Any]


class Land(Protocol):
    """
    What a band asks of the game it lives in.
    """

    params: Params
    era: str
    streams: Streams

    @property
    def season(self) -> str: ...

    def inside(self, x: int, y: int) -> bool: ...

    def biome(self, x: int, y: int) -> str: ...

    def river(self, x: int, y: int) -> bool: ...

    def value(self, name: str, x: int, y: int, season: str | None = None, stock: float | None = None) -> float: ...

    def deplete(self, x: int, y: int, name: str, amount: float) -> None: ...


@dataclass
class Member:
    age_days: int
    sex: str
    pregnant_until: int | None = None
    rest_until: int | None = None
    # The severity of a wound and the days of healing it still needs.
    wound: dict[str, Any] | None = None
    player: bool = False
    # The days of food and of water gone without since the last full ration.
    hungry: float = 0.0
    thirsty: float = 0.0
    role: str | None = None
    # The personal goods the member holds.
    kit: Stock = field(default_factory=Stock)
    # The days of sickness left.
    sick: float = 0.0
    # The goods made by the member, by good: its experience of each.
    craft: dict[str, float] = field(default_factory=dict)
    # The share of meat in its rations, carried over from day to day.
    meat: float = 0.0

    @classmethod
    def read(cls, plain: dict[str, Any]) -> Member:
        return cls(**{**plain, 'kit': Stock.read(plain['kit'])})

    def plain(self) -> dict[str, Any]:
        return {**asdict(self), 'kit': self.kit.plain()}


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
    wounds: dict[str, int]
    # What the hunters would gather, and the members sick.
    hunting: float
    sick: int


@dataclass
class Band:
    id: int
    x: int
    y: int
    members: list[Member]
    stores: Stock = field(default_factory=Stock)
    fatigue: float = 0.0
    states: list[str] = field(default_factory=list)
    action: Action = field(default_factory=lambda: {'kind': CAMP})
    intent: dict[str, Any] | None = None
    known: dict[Place, dict[str, Any]] = field(default_factory=dict)
    progress: float = 0.0
    target: Place | None = None
    reason: dict[str, Any] | None = None
    wander: dict[str, Any] | None = None
    dread: dict[Place, float] = field(default_factory=dict)
    unease: float = 0.0
    # The cells still ahead to the target of a go, and the day they were laid.
    route: dict[str, Any] | None = None
    # The parts of today out of camp_parts in which the band camped.
    camped: int = 0
    # The cell of a winter camp and the share of its building done.
    camp: dict[str, Any] | None = None
    # The cells of the winter camps the band has built, to come back to.
    camps: list[Place] = field(default_factory=list)
    # The members of roles that care sent to gather while the band goes short.
    freed: int = 0
    # The skills known and the counters they are learned by.
    lore: dict[str, Any] = field(default_factory=lores.fresh)
    # The goods made, spoiled and worn out not yet told, short of a whole unit.
    made: dict[str, float] = field(default_factory=dict)
    # The work done on goods not yet whole, and the quality of the materials spent on it summed.
    work: dict[str, list[float]] = field(default_factory=dict)
    spoiled: dict[str, float] = field(default_factory=dict)
    worn: dict[str, float] = field(default_factory=dict)
    # The season what the band remembers of the land is of.
    season: str = ''
    counted: tuple[int, Census] | None = field(default=None, init=False, repr=False, compare=False)
    laid: dict[Any, Params] = field(default_factory=dict, init=False, repr=False, compare=False)

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
            stores=Stock.read(plain['stores']),
            fatigue=plain['fatigue'],
            states=list(plain['states']),
            action=dict(plain['action']),
            intent=plain['intent'],
            known=known,
            progress=plain['progress'],
            target=None if target is None else (target[0], target[1]),
            reason=plain['reason'],
            wander=plain['wander'],
            dread={(held['x'], held['y']): held['amount'] for held in plain['dread']},
            unease=plain['unease'],
            route=plain['route'],
            camped=plain['camped'],
            camp=plain['camp'],
            camps=[(held['x'], held['y']) for held in plain['camps']],
            freed=plain['freed'],
            lore=copy.deepcopy(plain['lore']),
            made=dict(plain['made']),
            work={name: list(held) for name, held in plain['work'].items()},
            spoiled=dict(plain['spoiled']),
            worn=dict(plain['worn']),
            season=plain['season'],
        )

    @property
    def place(self) -> Place:
        return self.x, self.y

    @property
    def population(self) -> int:
        return len(self.members)

    def changed(self) -> None:
        """
        Forgets the census and the bonuses; called by whatever adds, removes, ages or hurts a member.
        """
        self.counted = None
        self.laid = {}

    def restocked(self) -> None:
        """
        Forgets the bonuses; called by whatever adds, takes, wears or hands out goods.
        """
        self.laid = {}

    def held(self, resource: str) -> float:
        return self.stores.held(resource)

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
            'stores': self.stores.plain(),
            'fatigue': self.fatigue,
            'states': list(self.states),
            'action': dict(self.action),
            'intent': self.intent,
            'known': [{'x': x, 'y': y, **self.known[x, y]} for x, y in sorted(self.known)],
            'progress': self.progress,
            'target': None if self.target is None else list(self.target),
            'reason': self.reason,
            'wander': self.wander,
            'dread': [{'x': x, 'y': y, 'amount': self.dread[x, y]} for x, y in sorted(self.dread)],
            'unease': self.unease,
            'route': self.route,
            'camped': self.camped,
            'camp': self.camp,
            'camps': [{'x': x, 'y': y} for x, y in self.camps],
            'freed': self.freed,
            'lore': copy.deepcopy(self.lore),
            'made': dict(sorted(self.made.items())),
            'work': {name: list(held) for name, held in sorted(self.work.items())},
            'spoiled': dict(sorted(self.spoiled.items())),
            'worn': dict(sorted(self.worn.items())),
            'season': self.season,
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
            WOUNDS: dict(counted.wounds),
            SICK: counted.sick,
            'stores': self.stores.amounts(),
            'goods': goods(params, self),
            KIT: kits(params, self),
            'fatigue': self.fatigue,
            'states': list(self.states),
            'action': dict(self.action),
            'intent': self.intent,
            'route': [] if self.route is None else [{'x': x, 'y': y} for x, y in self.route['cells']],
            'roles': roles(params, self),
            'camp': self.camp,
            'camps': [{'x': x, 'y': y} for x, y in self.camps],
            'reason': self.reason,
            'lore': list(self.lore[lores.KNOWN]),
        }

    def row(self, params: Params) -> list[Any]:
        totals = dict.fromkeys(SHORTAGES, 0.0)
        for name in self.stores:
            kind = params.resources[name].kind
            if kind in totals:
                totals[kind] += self.held(name)
        state = '+'.join(self.states) or NORMAL
        return [self.id, self.x, self.y, state, self.action['kind'], self.population, totals['food'], totals['water']]


def camp() -> Action:
    return {'kind': CAMP}


def building() -> Action:
    return {'kind': BUILD}


def gathering(shares: dict[str, float]) -> Action:
    """
    A gathering with the share of the gatherers that goes to every resource.
    """
    return {'kind': GATHER, 'shares': dict(shares)}


def moving(towards: str) -> Action:
    return {'kind': MOVE, 'towards': towards}


def roaming(towards: str) -> Action:
    return {'kind': ROAM, 'towards': towards}


def start(land: Land, x: int, y: int, day: int, rng: np.random.Generator) -> Band:
    """
    The band of the start: members of random age inside the start stage, none older than its oldest, and random
    sex, the first the player.
    """
    params = land.params
    rules = params.units.band
    low, high = bounds(params, rules.start.stage)
    if rules.start.oldest is not None:
        high = min(high, params.days(rules.start.oldest))
    count = rules.start.population
    ages = rng.integers(low, high, size=count)
    sexes = rng.integers(len(SEXES), size=count)
    members = [
        Member(int(age), SEXES[int(sex)], player=at == 0) for at, (age, sex) in enumerate(zip(ages, sexes, strict=True))
    ]
    stores = Stock({name: [[float(day), float(amount)]] for name, amount in rules.start.stores.items() if amount > 0})
    band = Band(id=1, x=x, y=y, members=members, stores=stores)
    assign(params, band)
    look(land, band, day)
    lores.begin(band)
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
    severities = people.injury.severities
    weakened = people.weakened
    sickness = people.sickness
    jobs = people.roles
    gatherers = eaters = carriers = pace = tires = hunting = 0.0
    voters = pregnant = sick = 0
    counts = dict.fromkeys(stages, 0)
    wounds = dict.fromkeys(severities, 0)
    for member, name in zip(band.members, named, strict=True):
        stage = stages[name]
        wound = None if member.wound is None else member.wound['severity']
        weak = any(wanting(params, member, name, prop) for prop in DEFICITS)
        counts[name] += 1
        job = 1.0 if member.role is None else jobs[member.role].gathers
        hurt = 1.0 if wound is None else severities[wound].gathers
        ill = member.sick > 0
        gathered = stage.gathers * hurt * (weakened.gathers if weak else 1.0) * (sickness.gathers if ill else 1.0) * job
        gatherers += gathered
        hunting += gathered if member.role == HUNTER else 0.0
        eaters += stage.eats
        carriers += stage.carries
        pace += (
            stage.pace
            * (1.0 if wound is None else severities[wound].pace)
            * (weakened.pace if weak else 1.0)
            * (sickness.pace if ill else 1.0)
        )
        tires += stage.tires
        voters += stage.votes
        pregnant += member.pregnant_until is not None
        sick += ill
        if wound is not None:
            wounds[wound] += 1
    many = max(len(named), 1)
    injured = sum(wounds.values())
    counted = Census(
        named,
        counts,
        gatherers,
        eaters,
        carriers,
        pace / many,
        tires / many,
        voters,
        pregnant,
        injured,
        wounds,
        hunting,
        sick,
    )
    band.counted = id(params), counted
    return counted


def people(params: Params, band: Band) -> list[dict[str, Any]]:
    """
    Every member as a record of the game keeps it: age, stage, sex, role, how it fares and the goods it holds.
    """
    everyone = common(params)
    return [
        {
            'age_days': member.age_days,
            'stage': name,
            'sex': member.sex,
            'player': member.player,
            'role': member.role or everyone,
            PREGNANT: member.pregnant_until is not None,
            'wound': None if member.wound is None else member.wound['severity'],
            SICK: member.sick > 0,
            'hungry': member.hungry,
            'thirsty': member.thirsty,
            KIT: [name for name in member.kit if member.kit.held(name) > 0],
            'craft': {good: round(mastery(params, member, good), 2) for good in sorted(member.craft)},
            MEAT: round(member.meat, 2),
        }
        for member, name in zip(band.members, census(params, band).stages, strict=True)
    ]


def common(params: Params) -> str:
    """
    The role of everyone no other role takes.
    """
    return next(
        name for name, role in params.units.band.people.roles.items() if role.cares is None and role.share is None
    )


def free(params: Params, band: Band) -> None:
    """
    Sends one more member of a role that cares to gather while a member went short today, and calls one back
    while the stores feed the band `leaves.back` days: docs/units/band.md, Roles.
    """
    back = params.days(params.units.band.people.leaves.back)
    if any(getattr(member, deficit) > NOTHING for member in band.members for deficit in DEFICITS.values()):
        band.freed = min(band.freed + 1, len(cared(params, band)))
    elif min(held_days(params, band, prop) for prop in DEFICITS) >= back:
        band.freed = max(band.freed - 1, 0)


def cared(params: Params, band: Band) -> list[tuple[int, str]]:
    """
    The members the children call for, with the role that cares each takes: carers until every child is cared
    for, each for the `cares` of its role with the bonuses of its own kit, a sling, laid over; never the player.
    The first is a woman of a stage that conceives - the pregnant and the resting first, then the oldest; the
    others are the elders first, the oldest first, then the women.
    """
    people = params.units.band.people
    named = census(params, band).stages
    children = sum(name == next(iter(people.stages)) for name in named)
    last = list(people.stages)[-1]
    elders = sorted(
        (
            at
            for at, (member, name) in enumerate(zip(band.members, named, strict=True))
            if name == last and not member.player
        ),
        key=lambda at: (-band.members[at].age_days, at),
    )
    women = sorted(
        (
            at
            for at, (member, name) in enumerate(zip(band.members, named, strict=True))
            if member.sex == FEMALE and not member.player and people.stages[name].conceives
        ),
        key=lambda at: (
            band.members[at].pregnant_until is None and band.members[at].rest_until is None,
            -band.members[at].age_days,
            at,
        ),
    )
    carers = iter([*women[:1], *elders, *women[1:]])
    taken: list[tuple[int, str]] = []
    for name, role in people.roles.items():
        left = float(children) if role.cares is not None else 0.0
        while left > NOTHING and (at := next(carers, None)) is not None:
            taken.append((at, name))
            left -= applied(params, band, band.members[at]).units.band.people.roles[name].cares or 0
    return taken


def crowded(params: Params, band: Band) -> bool:
    """
    Whether the children outnumber what the members of the roles that care care for, each by its own `cares`.
    """
    people = params.units.band.people
    children = census(params, band).counts[next(iter(people.stages))]
    cares = sum(
        applied(params, band, member).units.band.people.roles[member.role].cares or 0
        for member in band.members
        if member.role is not None and people.roles[member.role].cares is not None
    )
    return children > cares


def chosen(params: Params, band: Band, name: str) -> list[int]:
    """
    The members a role with a share takes once the band knows it: members of a stage that gathers, but the last,
    who hold no role that cares, never the player, men first and the youngest first, up to the share of the band
    rounded down.
    """
    role = params.units.band.people.roles.get(name)
    if role is None or role.share is None or not lores.opened(params, band, lores.ROLES, name):
        return []
    stages = params.units.band.people.stages
    last = list(stages)[-1]
    taken = (None, common(params), name)
    found = [
        at
        for at, (member, stage) in enumerate(zip(band.members, census(params, band).stages, strict=True))
        if not member.player and stage != last and stages[stage].gathers > 0 and member.role in taken
    ]
    found.sort(key=lambda at: (band.members[at].sex != MALE, band.members[at].age_days, at))
    return found[: math.floor(role.share * band.population + NOTHING)]


def assign(params: Params, band: Band) -> None:
    """
    Lays the roles anew: the members the children call for take their roles that care, but for the freed, the
    last of them; then those a role with a share takes that hold the good it needs; everyone else takes the role
    that cares for nobody.
    """
    taken = cared(params, band)
    for member in band.members:
        member.role = common(params)
    for at, name in taken[: max(len(taken) - band.freed, 0)]:
        band.members[at].role = name
    for name, role in params.units.band.people.roles.items():
        for at in chosen(params, band, name):
            if role.needs is None or band.members[at].kit.held(role.needs) > 0:
                band.members[at].role = name
    band.changed()


def roles(params: Params, band: Band) -> dict[str, int]:
    """
    The members by role; one with none yet counts in the common role.
    """
    found = dict.fromkeys(params.units.band.people.roles, 0)
    for member in band.members:
        found[member.role or common(params)] += 1
    return found


def reserve(params: Params, name: str, age_days: int, prop: str) -> float:
    """
    The days of food or of water a member of a stage at an age lives on once it ate and drank in full: its
    stage's, or in a stage that grows, nearing the next stage's over the span of the stage.
    """
    stages = params.units.band.people.stages
    stage = stages[name]
    own: float = getattr(stage.reserve, prop)
    if not stage.reserve.grows or stage.until is None:
        return own
    names = list(stages)
    at = names.index(name)
    before = stages[names[at - 1]].until if at else None
    begins = 0 if before is None else params.days(before)
    span = max(params.days(stage.until) - begins, 1)
    following: float = getattr(stages[names[at + 1]].reserve, prop)
    return own + (following - own) * min(max((age_days - begins) / span, 0.0), 1.0)


def left(params: Params, member: Member, name: str, prop: str) -> float:
    """
    The days of a reserve a member of a stage still has.
    """
    gone: float = getattr(member, DEFICITS[prop])
    return reserve(params, name, member.age_days, prop) - gone


def wanting(params: Params, member: Member, name: str, prop: str) -> bool:
    """
    Whether a member is hungry, or thirsty: it went short and a day or less of the reserve is left.
    """
    return getattr(member, DEFICITS[prop]) > NOTHING and left(params, member, name, prop) <= 1.0 + NOTHING


def voters(params: Params, band: Band) -> int:
    return census(params, band).voters


def enterable(land: Land, x: int, y: int) -> bool:
    """
    A cell of the window that can be walked into now.
    """
    return land.inside(x, y) and land.value(PASSABILITY, x, y) > 0


def _era(land: Land, x: int, y: int) -> Any:
    return land.params.biomes[land.biome(x, y)].eras[land.era]


def source(land: Land, at: Place, name: str) -> tuple[Place, float] | None:
    """
    The cell a band standing at a place gathers a resource from and the share of a gathering it gives: the place
    itself or a shore beside it that lists the resource, whole, or for goods any cell beside that lists them,
    `gathering_beside` of it; whichever gives most, the place first on a tie, then clockwise from the north.
    """
    resource = land.params.resources[name]
    beside = land.params.units.band.gathering_beside if resource.kind == GOODS else 0.0
    found: tuple[Place, float] | None = None
    best = -math.inf
    for dx, dy in [(0, 0), *DIRECTIONS.values()]:
        x, y = at[0] + dx, at[1] + dy
        if not land.inside(x, y):
            continue
        era = _era(land, x, y)
        share = 1.0 if not (dx or dy) or era.shore else beside
        if share <= 0 or name not in era.resources:
            continue
        value = land.value(resource.land, x, y) * share
        if value > best:
            found, best = ((x, y), share), value
    return found


def around(at: Place, reach: int) -> list[Place]:
    """
    The cells within reach of a place but the place itself: the first ring clockwise from the north, then every
    further ring by its rows.
    """
    found = [(at[0] + dx, at[1] + dy) for dx, dy in DIRECTIONS.values()] if reach >= 1 else []
    for far in range(2, reach + 1):
        found += [
            (at[0] + dx, at[1] + dy)
            for dy in range(-far, far + 1)
            for dx in range(-far, far + 1)
            if max(abs(dx), abs(dy)) == far
        ]
    return found


def ranging(band: Band) -> bool:
    """
    Whether the band gathers within the reach of a winter camp: it is bound to one, or stands on its camp, built
    or not.
    """
    proposal = None if band.intent is None else band.intent['proposal']
    camp = band.camp
    return (proposal is not None and proposal['kind'] == WINTER) or (
        camp is not None and (camp['x'], camp['y']) == band.place
    )


def reached(land: Land, band: Band, name: str) -> tuple[Place, float] | None:
    """
    The cell a band gathers a resource from and the share of a gathering it gives: its source, or while it
    ranges an enterable cell within reach that lists the resource, worth afar of its own; the earlier on a tie.
    """
    held = source(land, band.place, name)
    if not ranging(band):
        return held
    camp = land.params.units.band.winter_camp
    prop = land.params.resources[name].land
    best = -math.inf if held is None else land.value(prop, *held[0]) * held[1]
    for x, y in around(band.place, camp.reach):
        if not enterable(land, x, y) or name not in _era(land, x, y).resources:
            continue
        value = land.value(prop, x, y) * camp.afar
        if value > best:
            held, best = ((x, y), camp.afar), value
    return held


def speed(params: Params, band: Band) -> float:
    rules = applied(params, band).units.band
    pace = max(rules.speed.slowest, rules.speed.base - rules.speed.slowdown * band.population / 10)
    return pace * efficiency(rules, band) * census(params, band).pace


def efficiency(rules: Rules, band: Band) -> float:
    """
    The share of its pace and its gathering a band still has for its fatigue.
    """
    return 1.0 - rules.fatigue.slows * band.fatigue


def weight(params: Params, band: Band) -> float:
    """
    What the stores and the kits of the members weigh on the carry: the water the waterskins hold does not, and
    nothing kept in a built winter camp the band stands on does.
    """
    if sheltered(band):
        return 0.0
    held = band.stores.weight(params.resources) + sum(member.kit.weight(params.resources) for member in band.members)
    return held - min(_water(params, band), skins(params, band))


def skins(params: Params, band: Band) -> float:
    """
    The kilos of water the members carry beside their load, by the waterskins of their kits.
    """
    return sum(applied(params, band, member).units.band.carry_water_kg for member in band.members)


def _water(params: Params, band: Band) -> float:
    resources = params.resources
    return sum(band.held(name) * resources[name].weight_kg for name in band.stores if resources[name].kind == WATER)


def spare(params: Params, band: Band, name: str) -> float:
    """
    The kilos of a resource the waterskins still take beside the room: of water only.
    """
    if params.resources[name].kind != WATER:
        return 0.0
    return max(skins(params, band) - _water(params, band), 0.0)


def kits(params: Params, band: Band) -> dict[str, int]:
    """
    The members holding each personal good.
    """
    return {
        name: sum(member.kit.held(name) > 0 for member in band.members)
        for name, resource in params.resources.items()
        if resource.held == PERSONAL
    }


def goods(params: Params, band: Band) -> dict[str, float]:
    """
    The goods the band holds in its stores and its kits, per good.
    """
    found: dict[str, float] = {}
    for stock in (band.stores, *(member.kit for member in band.members)):
        for name in stock:
            if params.resources[name].kind == GOODS:
                found[name] = found.get(name, 0.0) + stock.held(name)
    return {name: found[name] for name in params.resources if found.get(name, 0.0) > 0}


def sheltered(band: Band) -> bool:
    """
    Whether the band stands on its winter camp and the camp is built.
    """
    camp = band.camp
    return camp is not None and (camp['x'], camp['y']) == band.place and camp['built'] >= 1.0


def appetite(params: Params, band: Band) -> float:
    """
    The share of its daily need a band eats and drinks: less in a winter camp.
    """
    return params.units.band.winter_camp.consumption if sheltered(band) else 1.0


def held_days(params: Params, band: Band, prop: str) -> float:
    """
    The days the stores of what feeds a need last the band, every resource of the kind of the property; endless when
    nobody eats it.
    """
    resources = [name for name, held in params.resources.items() if held.kind == prop]
    rates = applied(params, band).units.band.consumption_per_day
    eaten = census(params, band).eaters * appetite(params, band) * sum(rates.get(name, 0.0) for name in resources)
    return sum(band.held(name) for name in resources) / eaten if eaten > 0 else math.inf


def short(params: Params, band: Band, name: str) -> bool:
    """
    Whether the band holds fewer days of what a resource feeds than the top level of its needs asks.
    """
    top = max(level.days for level in params.units.band.decisions.levels.values())
    return held_days(params, band, params.resources[name].land) < top


def carry(params: Params, band: Band) -> float:
    """
    What the members carry by their stages, more for those whose kit lays a bonus on the carry and for those fed on
    meat. The bonus is net: a good that lays it, a litter, still weighs in the load and carries its own weight.
    """
    counted = census(params, band)
    stages = params.units.band.people.stages
    base = applied(params, band).units.band.carry_kg
    total = 0.0
    for member, name in zip(band.members, counted.stages, strict=True):
        own = applied(params, band, member).units.band.carry_kg if member.kit else base
        total += stages[name].carries * own * dieted(params, member, CARRIES)
        total += _carried(params, member) if member.kit else 0.0
    return total


def dieted(params: Params, member: Member, effect: str) -> float:
    """
    What the meat of a member's rations makes of an effect: nothing of it without meat, all of it on meat alone.
    """
    full: float = getattr(params.units.band.people.diet.full, effect)
    return 1.0 + (full - 1.0) * member.meat


def _carried(params: Params, member: Member) -> float:
    resources = params.resources
    return sum(
        member.kit.held(name) * resources[name].weight_kg
        for name in member.kit
        if any(
            bonus.to == TO_MEMBER and bonus.path == CARRY_KG and _holds(bonus, member.sex, None)
            for bonus in resources[name].gives
        )
    )


def room(params: Params, band: Band, name: str | None = None) -> float:
    """
    The carrying weight still free, in kilos; for a resource named, with what the waterskins still take of it.
    """
    free = max(carry(params, band) - weight(params, band), 0.0)
    return free if name is None else free + spare(params, band, name)


def act(land: Land, band: Band, action: Action, day: int) -> Action:
    """
    Carries one action out and gives it back as it was done: a move that cannot be made is a camp. The way into
    the next cell is kept over a camp and lost to a gather.
    """
    rules = land.params.units.band
    kind = action['kind']
    if kind == MOVE:
        done = _move(land, band, action, rules, 1.0)
    elif kind == ROAM:
        done = _roam(land, band, action, rules, day)
    elif kind == GATHER:
        done = _gather(land, band, action, rules, day)
    elif kind == BUILD:
        done = _build(land, band)
    else:
        done = camp()
    if done['kind'] in (GATHER, BUILD):
        band.progress, band.target = 0.0, None
    tired = getattr(rules.fatigue, done['kind'])
    if tired > 0:
        tired *= census(land.params, band).tires
    elif done['kind'] == CAMP and sheltered(band):
        tired *= rules.winter_camp.rest
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
        leave(land.params, band)
        band.x, band.y = target
        band.progress, band.target = 0.0, None
    return {'kind': action['kind'], 'towards': action['towards']}


def leave(params: Params, band: Band) -> None:
    """
    The band leaves its winter camp. What its members wear and carry, clothes, weapons and litters, goes with
    them, and the litters carry the food and the water: of the stores it leaves behind first the spare goods,
    then fresh food, then the reserve, then water, the oldest lots first, until a day of what it eats and drinks
    still fits on the carry; what is left stays in the camp.
    """
    stocked = sheltered(band)
    band.camp = None
    if not stocked:
        return
    eaters = census(params, band).eaters
    rates = params.units.band.consumption_per_day
    rations = sum(eaters * rate * params.resources[name].weight_kg for name, rate in rates.items())
    over = weight(params, band) + rations - carry(params, band)
    resources = params.resources

    def last(name: str) -> int:
        held = resources[name]
        return 0 if held.kind == GOODS else 3 if held.kind == WATER else 2 if held.reserve else 1

    for name in sorted(band.stores, key=last):
        if over > 0 and band.held(name) > 0:
            left = band.stores.part(name, min(band.held(name), over / resources[name].weight_kg))
            over -= left.weight(resources)
    band.restocked()


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
    """
    The gatherers split by the shares of the action: every share takes its resource from its own source, with
    the same share of the room. The hunters hunt instead.
    """
    free = room(land.params, band)
    counted = census(land.params, band)
    done: dict[str, float] = {}
    for name, share in action['shares'].items():
        held = reached(land, band, name)
        if held is not None and share > 0:
            hands = counted.gatherers - counted.hunting
            space = free * share + spare(land.params, band, name)
            _take(land, band, name, rules, day, share * held[1], held[0], space, hands)
            done[name] = share
    return gathering(done) if done else camp()


def _build(land: Land, band: Band) -> Action:
    """
    A part of work on the winter camp of the cell the band stands on; a camp elsewhere is given up.
    """
    params = land.params
    if band.camp is None or (band.camp['x'], band.camp['y']) != band.place:
        band.camp = {'x': band.x, 'y': band.y, 'built': 0.0}
    rules = params.units.band
    # The days of the build are counted in the parts a band works, not those it camps in.
    per_day = params.time.parts_per_day
    working = params.parts(rules.winter_camp.build) * (per_day - len(rules.camp_parts)) / per_day
    share = params.eras[land.era].parts_per_tick / working if working > 0 else 1.0
    band.camp['built'] = min(round(band.camp['built'] + share, 9), 1.0)
    if band.camp['built'] >= 1.0 and band.place not in band.camps:
        band.camps.append(band.place)
    return building()


def mend(band: Band) -> None:
    """
    A camp part of a band bound to winter on a camp it built before: the old camp is put in order over it, not
    built anew.
    """
    if band.intent is not None and band.intent['proposal']['kind'] == WINTER and band.place in band.camps:
        band.camp = {'x': band.x, 'y': band.y, 'built': 1.0}


def _take(
    land: Land,
    band: Band,
    name: str,
    rules: Rules,
    day: int,
    share: float,
    at: Place,
    free: float | None = None,
    hands: float | None = None,
) -> None:
    params = land.params
    resource = params.resources[name]
    gatherers = census(params, band).gatherers if hands is None else hands
    wanted = gatherers * rules.gathering.get(name, 0.0) * land.value(resource.land, *at)
    space = room(params, band, name) if free is None else free
    taken = min(wanted * share * efficiency(rules, band), space / resource.weight_kg)
    if resource.keep is not None:
        taken = min(taken, kept(params, band, name) - band.held(name))
    if taken > 0:
        band.stores.add(name, day, taken, _graded(land, resource, at))
        band.restocked()
        capacity = params.eras[land.era].capacity.get(resource.land)
        if capacity and _era(land, *at).properties[resource.land].recovery is not None:
            land.deplete(*at, resource.land, taken / capacity)


def hunt(land: Land, band: Band, day: int) -> None:
    """
    A tick the band stands: the hunters bring meat by the game of the cell, or of the best cell in the reach of a
    winter camp, and hides by the meat, as much as the room and the keep of the hides take; every hunter wears its
    spear by a hunt.
    """
    params = land.params
    rules = params.units.band
    hunters = census(params, band).hunting
    found = _hunted(land, band)
    if hunters <= 0 or found is None:
        return
    at, value = found
    resources = params.resources
    per = rules.hunting.hides
    meat = hunters * rules.hunting.meat * value * efficiency(rules, band)
    meat = min(meat, room(params, band) / (resources[MEAT].weight_kg + per * resources[HIDES].weight_kg))
    if meat <= NOTHING:
        return
    hides = meat * per
    if resources[HIDES].keep is not None:
        hides = min(hides, max(kept(params, band, HIDES) - band.held(HIDES), 0.0))
    band.stores.add(MEAT, day, meat)
    if hides > NOTHING:
        band.stores.add(HIDES, day, hides)
    for member in band.members:
        if member.role == HUNTER:
            wear(params, band, HUNTS, 1.0, (member.kit,))
    band.restocked()
    capacity = params.eras[land.era].capacity.get(GAME)
    if capacity and _era(land, *at).properties[GAME].recovery is not None:
        land.deplete(*at, GAME, meat / capacity)


def _hunted(land: Land, band: Band) -> tuple[Place, float] | None:
    """
    The cell the hunters hunt on and the game it gives: the own cell, or while the band ranges an enterable cell
    within reach worth afar of its own; the earlier on a tie, None without game.
    """
    found, best = band.place, land.value(GAME, *band.place)
    if ranging(band):
        camp = land.params.units.band.winter_camp
        for x, y in around(band.place, camp.reach):
            value = land.value(GAME, x, y) * camp.afar if enterable(land, x, y) else 0.0
            if value > best:
                found, best = (x, y), value
    return (found, best) if best > 0 else None


def _graded(land: Land, resource: Resource, at: Place) -> float | None:
    """
    The quality of a good gathered on a cell, drawn from the range of its biome; None for one without.
    """
    held = resource.quality.get(land.biome(*at))
    if held is None:
        return None
    return round(held.min + float(land.streams[GOODS].random()) * (held.max - held.min), 2)


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


def perceived(band: Band, at: Place, threat: float) -> float:
    """
    The threat of a cell as the band sees it: its own and the dread of what happened there.
    """
    return min(threat + band.dread.get(at, 0.0), 1.0)


def frighten(params: Params, band: Band) -> None:
    """
    An encounter hurt the band: its cell is dreaded.
    """
    band.dread[band.place] = band.dread.get(band.place, 0.0) + params.units.band.dread.encounter


def unsettle(params: Params, band: Band, threat: float) -> None:
    """
    The end of a day: unease grows with the threat the band sees where it stands and fades, and dread fades.
    """
    rules = params.units.band
    band.unease = band.unease * (1.0 - rules.unease.fade) + rules.unease.gain * perceived(band, band.place, threat)
    fall = rules.dread.encounter / max(params.days(rules.dread.lasts), 1)
    # What the steps of a float leave of a faded dread is not dread.
    band.dread = {at: held - fall for at, held in band.dread.items() if held - fall > fall * 1e-6}


def look(land: Land, band: Band, day: int) -> list[Place]:
    """
    Stores what the band sees around it and, when it forgets, drops what it saw too long ago; gives the cells
    that are news.
    """
    params = land.params
    rules = params.units.band
    names = params.eras[land.era].properties
    band.season = land.season
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
    if rules.memory is not None:
        oldest = day - params.parts(rules.memory) // params.time.parts_per_day
        for at in [at for at, cell in band.known.items() if cell['seen'] < oldest]:
            del band.known[at]
    return news


def reseason(land: Land, band: Band, was: str) -> list[Place]:
    """
    A new season: every cell the band remembers is expected as the season makes it, from the share it saw there
    of what the season before could give. Gives the cells whose memory changed.
    """
    names = land.params.eras[land.era].properties
    band.season = land.season
    changed: list[Place] = []
    for (x, y), cell in band.known.items():
        if not land.inside(x, y):
            continue
        held = dict(cell)
        for name in names:
            full, now = land.value(name, x, y, was, 1.0), land.value(name, x, y, None, 1.0)
            if full != now:
                held[name] = land.value(name, x, y, None, min(cell[name] / full, 1.0) if full > 0 else 1.0)
        if held != cell:
            band.known[x, y] = held
            changed.append((x, y))
    return changed


def spoil(params: Params, band: Band, day: int) -> None:
    """
    The day's end of the stores and the kits: drops the lots older than their resource keeps, by the bonuses
    held; a day in a winter camp ages them slower. The goods spoiled wait in the band's spoiled to be told.
    """
    per_day = params.time.parts_per_day
    ages = params.units.band.winter_camp.spoil if sheltered(band) else 1.0
    resources = applied(params, band).resources
    for stock in (band.stores, *(member.kit for member in band.members)):
        keeps = {
            name: params.parts(spoils) // per_day for name in stock if (spoils := resources[name].spoils) is not None
        }
        for name, amount in stock.spoil(day, keeps, ages).items():
            if params.resources[name].kind == GOODS:
                band.spoiled[name] = band.spoiled.get(name, 0.0) + amount
    band.restocked()


def wear(params: Params, band: Band, use: str, uses: float, stocks: Iterable[Stock] | None = None) -> None:
    """
    Wears the goods held that serve a use, of the stocks given or of the stores and then the kits; what wore out
    waits in the band's worn to be told.
    """
    held = (band.stores, *(member.kit for member in band.members)) if stocks is None else tuple(stocks)
    for name, resource in params.resources.items():
        serves = resource.wears.get(use)
        if serves is None:
            continue
        left = uses
        for stock in held:
            worn, left = stock.wear(name, left, serves)
            if worn > 0:
                band.worn[name] = band.worn.get(name, 0.0) + worn
                band.restocked()


def pull(params: Params, band: Band) -> None:
    """
    A day on the march: every member wears what it pulls by a day, and the goods in the stores do not wear.
    """
    for member in band.members:
        wear(params, band, PULLED, 1.0, (member.kit,))


def told(lost: dict[str, float]) -> dict[str, int]:
    """
    The whole units of goods made or lost, taken out of the tally; the rest waits for the next.
    """
    whole = {name: math.floor(amount + 1e-9) for name, amount in lost.items()}
    whole = {name: count for name, count in whole.items() if count > 0}
    for name, count in whole.items():
        lost[name] = max(lost[name] - count, 0.0)
    return whole


@dataclass
class Meal:
    """
    What a day of eating did: the share of each need met and the members it made sick.
    """

    met: dict[str, float]
    sickened: int = 0


def eat(params: Params, band: Band, rng: np.random.Generator | None = None) -> Meal:
    """
    The people eat and drink for a day, the oldest lots first, a ration of food of every food held. What there is
    goes first to whoever has the least of that reserve left, children first on a tie; a full ration fills the
    reserve again, a part of it spends what was missing. The share of meat in what the band ate goes into the diet
    of every member. With a stream given, a member who ate food that sickens falls sick by its chance times the
    share of its ration that was of it.
    """
    rules = params.units.band
    stages = rules.people.stages
    named = census(params, band).stages
    order = {name: at for at, name in enumerate(stages)}
    eating = appetite(params, band)
    shares: dict[str, list[float]] = {}
    met: dict[str, float] = {}
    eaten = tainted = meat = 0.0
    for name, rate in applied(params, band).units.band.consumption_per_day.items():
        prop = params.resources[name].property or ''
        rations = [stages[stage].eats * rate * eating for stage in named]
        need = sum(rations)
        if params.resources[name].kind == FOOD:
            missing, foods = _feed(params, band, need)
            eaten += need - missing
            meat += foods.get(rules.people.diet.meat, 0.0)
            sickens = sum(amount * (params.resources[food].sickens or 0.0) for food, amount in foods.items())
            tainted = sickens / (need - missing) if need - missing > NOTHING else 0.0
        else:
            missing = band.stores.take(name, need)
        met[name] = 1.0 if need <= 0 else (need - missing) / need
        if prop not in DEFICITS:
            continue
        given = need - missing
        got = [1.0] * len(named)
        first = sorted(
            range(len(named)),
            key=lambda at: (left(params, band.members[at], named[at], prop), order[named[at]], at),
        )
        for at in first:
            if rations[at] > 0:
                taken = min(rations[at], given)
                given -= taken
                got[at] = taken / rations[at]
        shares[prop] = [min(a, b) for a, b in zip(shares.get(prop, got), got, strict=True)]
    for prop, got in shares.items():
        for member, share in zip(band.members, got, strict=True):
            gone = 0.0 if share >= 1.0 - NOTHING else getattr(member, DEFICITS[prop]) + 1.0 - share
            setattr(member, DEFICITS[prop], round(gone, 9))
    if eaten > NOTHING:
        _diet(params, band, meat / eaten)
    wear(params, band, EATEN, eaten)
    sickened = 0
    if rng is not None and tainted > 0:
        fed = shares.get(FOOD, [1.0] * len(named))
        chances = [0.0 if member.sick > 0 else tainted * share for member, share in zip(band.members, fed, strict=True)]
        sickened = sicken(params, band, _chanced(rng, chances))
    band.changed()
    return Meal(met, sickened)


def _diet(params: Params, band: Band, today: float) -> None:
    """
    The share of meat in the rations of every member after a day the band ate that share of meat.
    """
    keeps = params.units.band.people.diet.keeps
    for member in band.members:
        member.meat = round(member.meat * keeps + today * (1.0 - keeps), 9)


def _feed(params: Params, band: Band, need: float) -> tuple[float, dict[str, float]]:
    """
    Takes a ration out of every food held, the oldest lots first across them and a reserve after every other; a
    unit of a lot feeds its quality. Gives what is still missing and what each food fed.
    """
    resources = params.resources
    foods = [name for name, resource in resources.items() if resource.kind == FOOD]
    lots = sorted(
        (resources[name].reserve, lot[0], at, order, lot[1], lot[2] if len(lot) > 2 else 1.0)
        for at, name in enumerate(foods)
        for order, lot in enumerate(band.stores.get(name, []))
    )
    missing = need
    taken: dict[str, float] = {}
    for _, _, at, _, amount, quality in lots:
        part = min(amount * quality, missing)
        if part <= 0 or quality <= 0:
            continue
        band.stores.take(foods[at], part / quality)
        taken[foods[at]] = taken.get(foods[at], 0.0) + part
        missing -= part
        if missing <= NOTHING:
            break
    return max(missing, 0.0), taken


def sicken(params: Params, band: Band, picked: list[int]) -> int:
    """
    The members picked fall sick for the days a sickness lasts.
    """
    lasts = float(params.days(params.units.band.people.sickness.lasts))
    for at in picked:
        band.members[at].sick = lasts
    if picked:
        band.changed()
    return len(picked)


def cure(params: Params, band: Band) -> int:
    """
    The end of a day: while a cure is held, one is spent on every sick member, whose sickness ends, then on every
    wound a cure shortens not treated yet, whose days left it cuts. Gives the people cured.
    """
    severities = params.units.band.people.injury.severities
    cured = 0
    for member in band.members:
        if member.sick > 0 and _spend(params, band):
            member.sick = 0.0
            cured += 1
    for member in band.members:
        wound = member.wound
        if wound is None or wound.get('treated') or severities[wound['severity']].treated >= 1.0:
            continue
        if _spend(params, band):
            wound['left'] = round(wound['left'] * severities[wound['severity']].treated, 9)
            wound['treated'] = True
            cured += 1
    if cured:
        band.changed()
    return cured


def _spend(params: Params, band: Band) -> bool:
    """
    Spends a cure of the stores, the oldest goods that serve one first; False when less than one is held.
    """
    held = 0.0
    for name, resource in params.resources.items():
        serves = resource.wears.get(CURES)
        if serves is not None:
            held += sum(lot[1] * serves * (lot[2] if len(lot) > 2 else 1.0) for lot in band.stores.get(name, []))
    if held < 1.0 - NOTHING:
        return False
    wear(params, band, CURES, 1.0, (band.stores,))
    return True


def suffer(params: Params, band: Band, day: int) -> tuple[list[str], list[str], list[tuple[str, int]]]:
    """
    What a day of eating did: every member with nothing left of a reserve dies, but the player, and the band
    starves or thirsts while one of its members does. Gives the states that began, those that ended, and the
    people lost by cause.
    """
    lost: list[tuple[str, int]] = []
    for prop, (_, cause) in SHORTAGES.items():
        named = census(params, band).stages
        dead = [
            at
            for at, (member, name) in enumerate(zip(band.members, named, strict=True))
            if not member.player and left(params, member, name, prop) <= NOTHING
        ]
        if dead:
            lost.append((cause, bury(params, band, dead, day)))
    began: list[str] = []
    ended: list[str] = []
    named = census(params, band).stages
    for prop, (state, _) in SHORTAGES.items():
        now = any(wanting(params, member, name, prop) for member, name in zip(band.members, named, strict=True))
        if now and state not in band.states:
            began.extend(_begin(band, state))
        elif not now and state in band.states:
            band.states.remove(state)
            ended.append(state)
    return began, ended, lost


def vulnerable(params: Params, band: Band, cause: str, season: str | None = None) -> list[float]:
    """
    How much each member is exposed to a cause, by stage and age, by what its goods leave of it in the season and,
    for frailty, more while it is sick and less by the meat it eats; the player never dies.
    """
    named = census(params, band).stages
    sickness = params.units.band.people.sickness
    found = []
    for member, name in zip(band.members, named, strict=True):
        held = 0.0 if member.player else exposed(params, name, member.age_days, cause)
        if held > 0:
            held *= getattr(applied(params, band, member, season).units.band.people.exposure, cause, 1.0)
            held *= sickness.frailty if cause == FRAILTY and member.sick > 0 else 1.0
            held *= dieted(params, member, FRAILTY) if cause == FRAILTY else 1.0
        found.append(held)
    return found


def exposed(params: Params, name: str, age_days: int, cause: str) -> float:
    """
    The weight of a cause for a member of a stage at an age: its stage's own, or, when the stage settles, the next
    stage's plus the difference halved for every span of settles lived in the stage.
    """
    stages = params.units.band.people.stages
    stage = stages[name]
    own = getattr(stage.dies, cause)
    if stage.settles is None:
        return float(own)
    names = list(stages)
    at = names.index(name)
    before = stages[names[at - 1]].until if at else None
    begins = 0 if before is None else params.days(before)
    following = getattr(stages[names[at + 1]].dies, cause)
    return float(following + (own - following) * 0.5 ** ((age_days - begins) / params.days(stage.settles)))


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


def bury(params: Params, band: Band, picked: list[int], day: int) -> int:
    """
    The members picked die; their goods go back to the stores.
    """
    for at in sorted(picked, reverse=True):
        stow(params, band, band.members[at].kit, day)
        del band.members[at]
    if picked:
        band.changed()
    return len(picked)


def struck(
    params: Params,
    band: Band,
    day: int,
    taken: float,
    hurt: float,
    wounds: dict[str, float],
    rng: np.random.Generator,
    sickens: bool = False,
) -> tuple[int, int, int]:
    """
    What an encounter does: the share taken of the people, weighed by how exposed they are, die, but for one that
    sickens, which leaves sick instead the first of them while a cure is held for each; the share hurt of those
    left is wounded by the weights of its kind, the usual ones when it has none. Gives the dead, the injured and
    the sick.
    """
    weights = vulnerable(params, band, ENCOUNTER)
    picked = _drawn(rng, weights, int(taken * sum(weights) + 0.5))
    saved: list[int] = []
    while sickens and len(saved) < len(picked) and _spend(params, band):
        saved.append(picked[len(saved)])
    sickened = sicken(params, band, saved)
    dead = bury(params, band, picked[len(saved) :], day)
    weights = _injurable(params, band)
    picked = _drawn(rng, weights, int(hurt * sum(weights) + 0.5))
    return dead, _injure(params, band, picked, wounds or params.units.band.people.injury.drawn, rng), sickened


def _injurable(params: Params, band: Band) -> list[float]:
    named = census(params, band).stages
    return [
        0.0 if member.wound is not None else exposed(params, name, member.age_days, INJURY)
        for member, name in zip(band.members, named, strict=True)
    ]


def _injure(params: Params, band: Band, picked: list[int], weights: dict[str, float], rng: np.random.Generator) -> int:
    """
    Wounds the members picked, each of a severity drawn by the weights; nothing is drawn when nobody is picked.
    """
    if not picked:
        return 0
    severities = params.units.band.people.injury.severities
    names = [name for name, held in weights.items() if held > 0]
    bounds = np.cumsum([weights[name] for name in names]) / sum(weights.values())
    for at, drawn in zip(picked, rng.random(len(picked)), strict=True):
        name = names[min(int(np.searchsorted(bounds, drawn, side='right')), len(names) - 1)]
        band.members[at].wound = {'severity': name, 'left': float(severities[name].days)}
    band.changed()
    return len(picked)


def fed(params: Params, band: Band) -> float:
    """
    How well the band can feed more children: the share of `birth.stores` its food in the stores lasts, up to
    whole; nothing while it starves or thirsts.
    """
    if STARVATION in band.states or THIRST in band.states:
        return 0.0
    days = max(params.days(params.units.band.people.birth.stores), 1)
    return min(held_days(params, band, 'food') / days, 1.0)


def dry(params: Params, band: Band, day: int) -> None:
    """
    The end of a day of a season of drying, for a band that knows how to make the reserve: the food left over
    tomorrow's ration dries by itself into it, a unit of it feeding `drying.keeps` of a ration.
    """
    drying = params.units.band.drying
    if band.season not in drying.seasons or not lores.opened(params, band, lores.MAKES, drying.into):
        return
    left = _spare(params, band, drying.of)
    if left <= NOTHING:
        return
    band.stores.part(drying.of, left)
    band.stores.add(drying.into, day, left, drying.keeps)
    band.restocked()


@dataclass
class Lived:
    """
    What a day did to the members of a band.
    """

    lost: list[tuple[str, int]] = field(default_factory=list)
    born: int = 0
    injured: int = 0


def live(
    params: Params,
    band: Band,
    day: int,
    wellbeing: float,
    feeds: float,
    camped: float,
    rng: np.random.Generator,
    season: str | None = None,
) -> Lived:
    """
    The day of the members at its end: they age, get better, die of age and frailty, heal or are hurt, give birth,
    conceive and are cared for. Camped is the share of the active parts of the day the band camped: it heals faster
    and dies less of frailty; meat heals faster too. The goods of a member that guard it in a season do so in the
    season given.
    """
    rules = params.units.band
    people = rules.people
    per_year = params.time.days_per_year
    lived = Lived()
    heals = 1.0 + (people.injury.heal_in_camp - 1.0) * camped
    for member in band.members:
        member.age_days += 1
        if member.wound is not None:
            # Rounded so that shares of a day add up to the whole days of a wound.
            member.wound['left'] = round(member.wound['left'] - heals * dieted(params, member, HEALS), 9)
            if member.wound['left'] <= 0:
                member.wound = None
        if member.rest_until is not None and member.rest_until <= day:
            member.rest_until = None
        if member.sick > 0:
            member.sick = max(member.sick - 1.0, 0.0)
    band.changed()
    begins = [params.days(applied(params, band, member).units.band.people.age.begins) for member in band.members]
    doubles = params.days(people.age.doubles)
    old = [
        (
            0.0
            if member.player or member.age_days < begun
            else min(people.age.per_year * 2 ** ((member.age_days - begun) / doubles), 1.0) / per_year
        )
        for member, begun in zip(band.members, begins, strict=True)
    ]
    lived.lost.append((AGE, bury(params, band, _chanced(rng, old), day)))
    sheltered = 1.0 - (1.0 - rules.shelter.frailty) * camped
    weights = vulnerable(params, band, FRAILTY, season)
    frail = [held * (1.0 - wellbeing) * sheltered / per_year for held in weights]
    lived.lost.append((FRAILTY, bury(params, band, _chanced(rng, frail), day)))
    hurt = [
        held * applied(params, band, member).units.band.people.injury.per_day
        for held, member in zip(_injurable(params, band), band.members, strict=True)
    ]
    lived.injured = _injure(params, band, _chanced(rng, hurt), people.injury.drawn, rng)
    lived.born, mothers = _births(params, band, day, rng)
    lived.lost.append((BIRTH, bury(params, band, mothers, day)))
    if feeds > 0:
        _conceive(params, band, day, rng, feeds)
    _nurse(params, band)
    free(params, band)
    assign(params, band)
    lived.lost = [(cause, count) for cause, count in lived.lost if count]
    return lived


def _nurse(params: Params, band: Band) -> None:
    """
    A day of the carers: each wears what it carries the children in by a day, and a day the children outnumber
    what the carers care for is counted.
    """
    roles = params.units.band.people.roles
    for member in band.members:
        if member.role is not None and roles[member.role].cares is not None:
            wear(params, band, CARRIED, 1.0, (member.kit,))
    if crowded(params, band):
        lores.crowd(band)


def _chanced(rng: np.random.Generator, chances: list[float]) -> list[int]:
    """
    The members whose chance came up; one number is drawn for every member whatever its chance.
    """
    drawn = rng.random(len(chances))
    return [at for at, chance in enumerate(chances) if drawn[at] < chance]


def _births(params: Params, band: Band, day: int, rng: np.random.Generator) -> tuple[int, list[int]]:
    """
    The children born alive today and the mothers who died of it. Once the band knows midwifery, the oldest woman
    but the mother attends a birth, and a herb held is spent on it.
    """
    birth = params.units.band.people.birth
    low, high = params.days(birth.pause.min), params.days(birth.pause.max)
    women = sorted(
        (at for at, member in enumerate(band.members) if member.sex == FEMALE),
        key=lambda at: (-band.members[at].age_days, at),
    )
    skilled = lores.known(band, lores.MIDWIFERY)
    born: list[Member] = []
    mothers: list[int] = []
    delivered = 0
    for at, member in enumerate(band.members):
        if member.pregnant_until is None or member.pregnant_until > day:
            continue
        lives, dies, sex, pause = rng.random(), rng.random(), rng.integers(len(SEXES)), rng.integers(low, high + 1)
        member.pregnant_until, member.rest_until = None, day + int(pause)
        delivered += 1
        survives, risk = birth.child_survives, birth.mother_dies
        if skilled and any(woman != at for woman in women):
            attended = birth.midwife.herb if _spend(params, band) else birth.midwife
            survives, risk = attended.survives, risk * attended.mother
        if lives < survives:
            born.append(Member(0, SEXES[int(sex)]))
        if dies < risk and not member.player:
            mothers.append(at)
    band.members.extend(born)
    lores.delivered(band, delivered)
    band.changed()
    return len(born), mothers


def _conceive(params: Params, band: Band, day: int, rng: np.random.Generator, stored: float = 1.0) -> None:
    """
    Every woman of a stage that conceives, neither pregnant, resting, hungry nor thirsty, may conceive while such
    a man lives, at the chance of a day times the share of the stores fed.
    """
    people = params.units.band.people
    named = census(params, band).stages
    able = [
        people.stages[name].conceives and not any(wanting(params, member, name, prop) for prop in DEFICITS)
        for member, name in zip(band.members, named, strict=True)
    ]
    if not any(member.sex == MALE and can for member, can in zip(band.members, able, strict=True)):
        return
    drawn = rng.random(len(band.members))
    pregnancy = max(params.days(people.birth.pregnancy), 1)
    for at, (member, can) in enumerate(zip(band.members, able, strict=True)):
        ready = can and member.sex == FEMALE and member.pregnant_until is None and member.rest_until is None
        if ready and drawn[at] < people.birth.conceive_per_day * stored:
            member.pregnant_until = day + pregnancy
    band.changed()


def eligible(params: Params, band: Band, per: str) -> list[int]:
    """
    The members a keep counts, in the order goods are handed to them: every member and head the least protected
    first, children, elders, then adults; adults before elders; pullers, the adults of the common role who gather,
    men first; hunters, those the role would take; nannies, the carers in the order they are called. The youngest
    first in each but the nannies: docs/game/skills.md, Handing out.
    """
    if per == HUNTER:
        return chosen(params, band, HUNTER)
    if per == NANNY:
        taken = cared(params, band)
        return [at for at, _ in taken[: max(len(taken) - band.freed, 0)]]
    people = params.units.band.people
    names = list(people.stages)
    first, last = names[0], names[-1]
    named = census(params, band).stages
    everyone = common(params)

    def fits(member: Member, name: str) -> bool:
        if per == ADULT:
            return name != first
        if per == PULLER:
            return name not in (first, last) and people.stages[name].gathers > 0 and member.role in (None, everyone)
        return True

    def rank(at: int) -> tuple[int, int, int]:
        member, name = band.members[at], named[at]
        if per == PULLER:
            before = int(member.sex != MALE)
        elif per == ADULT:
            before = int(name == last)
        else:
            before = 0 if name == first else 1 if name == last else 2
        return before, member.age_days, at

    found = [at for at, (member, name) in enumerate(zip(band.members, named, strict=True)) if fits(member, name)]
    return sorted(found, key=rank)


def kept(params: Params, band: Band, name: str) -> float:
    """
    How much of a good the band wants to hold by its keep; nothing for a good without one.
    """
    keep = params.resources[name].keep
    return 0.0 if keep is None else keep.amount * len(eligible(params, band, keep.per))


def stow(params: Params, band: Band, kit: Stock, day: int) -> None:
    """
    Puts a kit into the stores: what is left of a good less than whole is taken apart into the materials of its
    recipe, by that share and at its quality, so the stores hold made goods whole only.
    """
    for name, lots in kit.items():
        made = params.resources[name].made
        for lot in lots:
            piece = lot[1] - math.floor(lot[1] + NOTHING) if made else 0.0
            if piece > NOTHING:
                quality = lot[2] if len(lot) > 2 else None
                for material, amount in made.items():
                    band.stores.add(material, day, piece * amount, quality)
            if lot[1] - piece > NOTHING:
                band.stores.join(Stock({name: [[lot[0], lot[1] - piece, *lot[2:]]]}))


def hand_out(params: Params, band: Band, day: int) -> None:
    """
    The evening: a personal good goes back to the stores from a holder who may no longer use it, then to those its
    keep counts who lack it, in their order and whole only: a worn one counts as one and is not topped up.
    """
    for name, resource in params.resources.items():
        if resource.held != PERSONAL:
            continue
        keep = resource.keep
        takers = [] if keep is None else eligible(params, band, keep.per)
        for at, member in enumerate(band.members):
            if at not in takers and member.kit.held(name) > 0:
                stow(params, band, member.kit.part(name, member.kit.held(name)), day)
        for at in takers:
            kit = band.members[at].kit
            wanted = 0.0 if keep is None else keep.amount - math.ceil(kit.held(name) - NOTHING)
            given = math.floor(min(wanted, band.held(name)) + NOTHING)
            if given > 0:
                kit.join(band.stores.part(name, float(given)))
    band.restocked()


def make(params: Params, band: Band, day: int) -> None:
    """
    A camp part: of the goods the band knows how to make, the one furthest below its keep whose materials are held
    is worked on by its most experienced makers, members of a stage that gathers, each at
    `making.per_part`, of the oldest lots of the materials; each gains the experience of its work. A good goes into
    the stores whole, at the mean quality of the materials spent on it times what the makers' mastery leaves of
    it; the rest of the work waits in the band's work. What was made waits in the band's made to be told.
    """
    making = params.units.band.making
    found: tuple[float, str, float] | None = None
    for name, resource in params.resources.items():
        if not resource.made or not lores.opened(params, band, lores.MAKES, name):
            continue
        wants = kept(params, band, name)
        wanted = math.ceil(wants - whole(band, name) - NOTHING) - band.work.get(name, [0.0, 0.0])[0]
        possible = min(_spare(params, band, material) / amount for material, amount in resource.made.items())
        if wanted > NOTHING and possible > NOTHING:
            missing = wanted / wants
            if found is None or missing > found[0]:
                found = missing, name, min(wanted, possible)
    if found is None:
        return
    _, name, most = found
    hands = makers(params, band, name)
    amount = min(making.per_part * len(hands), most)
    if amount <= NOTHING:
        return
    graded = units = 0.0
    for material, needed in params.resources[name].made.items():
        for lot in band.stores.part(material, needed * amount).get(material, []):
            graded += lot[1] * (lot[2] if len(lot) > 2 else 1.0)
            units += lot[1]
    skill = sum(mastery(params, band.members[at], name) for at in hands) / len(hands)
    floor = making.mastery.floor
    for at in hands:
        crafted = band.members[at].craft
        crafted[name] = crafted.get(name, 0.0) + amount / len(hands)
    work = band.work.setdefault(name, [0.0, 0.0])
    work[0] += amount
    work[1] += amount * graded / units * (floor + (1.0 - floor) * skill)
    done = math.floor(work[0] + NOTHING)
    if done > 0:
        quality = round(work[1] / work[0], 2)
        rest = max(work[0] - done, 0.0)
        band.stores.add(name, day, float(done), quality)
        band.made[name] = band.made.get(name, 0.0) + done
        band.work[name] = [rest, rest * quality]
        band.restocked()
    if band.work[name][0] <= NOTHING:
        del band.work[name]


def _spare(params: Params, band: Band, name: str) -> float:
    """
    What of a material making may take: all of a good, of a food what is over the band's ration of a day.
    """
    held = band.held(name)
    if params.resources[name].kind != FOOD:
        return held
    rate = params.units.band.consumption_per_day.get(name, 0.0)
    return max(held - census(params, band).eaters * rate * appetite(params, band), 0.0)


def makers(params: Params, band: Band, name: str) -> list[int]:
    """
    The members who make a good in a camp part: of a stage that gathers, the most experienced of it first, then
    the oldest, up to `making.hands`.
    """
    stages = params.units.band.people.stages
    able = [at for at, stage in enumerate(census(params, band).stages) if stages[stage].gathers > 0]
    members = band.members
    able.sort(key=lambda at: (-members[at].craft.get(name, 0.0), -members[at].age_days, at))
    return able[: params.units.band.making.hands]


def mastery(params: Params, member: Member, name: str) -> float:
    """
    A member's mastery of a good, from 0 to nearly 1: its experience over that and the half of mastery.
    """
    done = member.craft.get(name, 0.0)
    return done / (done + params.units.band.making.mastery.half)


def whole(band: Band, name: str) -> float:
    """
    The goods of a kind the band holds as things: the stores as they are, every kit holding one as one, worn or not.
    """
    return band.stores.held(name) + sum(math.ceil(member.kit.held(name) - NOTHING) for member in band.members)


def shared(params: Params, band: Band, name: str) -> float:
    """
    The share a good lays its bonuses on the band by: of its keep held for a common good, of those its keep counts
    holding one for a personal good; all of it for a good without a keep while any is held.
    """
    resource = params.resources[name]
    if resource.held == PERSONAL:
        counted = range(band.population) if resource.keep is None else eligible(params, band, resource.keep.per)
        holding = sum(band.members[at].kit.held(name) > 0 for at in counted)
        return holding / len(counted) if counted else 0.0
    held, wanted = band.held(name), kept(params, band, name)
    if resource.keep is None:
        return 1.0 if held > 0 else 0.0
    return min(held / wanted, 1.0) if wanted > 0 else 0.0


def filled(params: Params, band: Band, name: str) -> float:
    """
    The share of a role with a share its members fill: of the members it would take by the share of the band.
    """
    role = params.units.band.people.roles[name]
    quota = 0 if role.share is None else math.floor(role.share * band.population + NOTHING)
    return min(sum(member.role == name for member in band.members) / quota, 1.0) if quota > 0 else 0.0


def applied(params: Params, band: Band, member: Member | None = None, season: str | None = None) -> Params:
    """
    The tree with the bonuses of the goods held and the roles filled laid over it: those on the band by their
    share and, for a member, those of its own kit; a bonus of a sex or of seasons only for them. Kept until the
    goods or the members change.
    """
    worn = () if member is None else tuple(name for name in sorted(member.kit) if member.kit.held(name) > 0)
    key = (id(params), season, None if member is None or not worn else (member.sex, worn))
    if key in band.laid:
        return band.laid[key]
    if member is not None and worn:
        bonuses = [
            (bonus, 1.0)
            for name in worn
            for bonus in params.resources[name].gives
            if bonus.to == TO_MEMBER and _holds(bonus, member.sex, season)
        ]
        laid = _lay(params, applied(params, band, None, season), bonuses)
    else:
        bonuses = [
            (bonus, share)
            for name, resource in params.resources.items()
            for bonus in resource.gives
            if bonus.to == TO_BAND and _holds(bonus, None, season) and (share := shared(params, band, name)) > 0
        ]
        bonuses += [
            (bonus, share)
            for name, role in params.units.band.people.roles.items()
            for bonus in role.gives
            if _holds(bonus, None, season) and (share := filled(params, band, name)) > 0
        ]
        laid = _lay(params, params, bonuses)
    band.laid[key] = laid
    return laid


def _holds(bonus: Bonus, sex: str | None, season: str | None) -> bool:
    return (bonus.sex is None or bonus.sex == sex) and (not bonus.seasons or season in bonus.seasons)


def _lay(params: Params, tree: Params, bonuses: list[tuple[Bonus, float]]) -> Params:
    """
    Lays bonuses over a tree, each by its share: {times: x} as 1 + (x - 1) * share, {plus: x} as x * share; the
    pluses of a path are added before its times multiply.
    """
    over: dict[str, list[float]] = {}
    for bonus, share in bonuses:
        held = over.setdefault(bonus.path, [0.0, 1.0])
        if bonus.times is not None:
            held[1] *= 1.0 + (bonus.times - 1.0) * share
        elif isinstance(bonus.plus, Duration):
            held[0] += params.days(bonus.plus) * share
        elif bonus.plus is not None:
            held[0] += bonus.plus * share
    for path, (plus, times) in over.items():
        tree = _over(params, tree, path.split('.'), plus, times)
    return tree


def _over(params: Params, node: Any, names: list[str], plus: float, times: float) -> Any:
    if not names:
        if isinstance(node, Duration):
            return Duration(days=round((params.days(node) + plus) * times))
        return (node + plus) * times
    name, rest = names[0], names[1:]
    if isinstance(node, dict):
        return {**node, name: _over(params, node[name], rest, plus, times)}
    return node.model_copy(update={name: _over(params, getattr(node, name), rest, plus, times)})
