"""
What the seat sees while a council waits for it, as numbers; the features of its options and the score a mind gives
them: docs/lab/players.md.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any

from ..content import FEATURES, GOODS, PERSONAL, Mind, Params
from . import band as bands
from . import council, decisions, lore, routes
from .band import Band
from .clock import SeasonSchedule
from .commands import ABSTAIN, GO, STAY, WINTER

if TYPE_CHECKING:
    from .game import Game

FOOD = 'food'
WATER = 'water'
THREAT = 'threat'
PASSABILITY = 'passability'
SEAT = 'player'


@dataclass(frozen=True)
class Ground:
    """
    The place of an option as the band knows it; land it does not know is what it expects of such land. `route`
    is the cells of the way there, 0 where the band stands and None when it knows no way.
    """

    biome: str | None
    food: float
    water: float
    threat: float
    passability: float
    river: bool
    unknown: bool
    route: int | None


@dataclass(frozen=True)
class Option:
    """
    One answer the seat may give, numbered from 1 in the order of the table; abstaining is the last.
    """

    number: int
    proposal: dict[str, Any]
    key: str
    votes: int
    leads: bool
    score: float
    ground: Ground | None

    @property
    def kind(self) -> str:
        return str(self.proposal['kind'])


@dataclass(frozen=True)
class Observation:
    """
    The date, the band, the seat and the table of the council, only what the seat sees.
    """

    year: int
    month: int
    day: int
    part: str
    season: str
    people: dict[str, int]
    pregnant: int
    injured: int
    sick: int
    states: tuple[str, ...]
    fatigue: float
    food_days: float
    water_days: float
    hunger: float
    thirst: float
    skills: tuple[str, ...]
    goods: dict[str, float]
    kits: dict[str, int]
    status: float
    voice: float
    occasion: str | None
    sight: int
    winter_left: float
    options: tuple[Option, ...]

    @property
    def leader(self) -> Option | None:
        return next((option for option in self.options if option.leads), None)


def observe(game: Game) -> Observation | None:
    """
    What the seat sees while the council of the day waits for it; None while none does.
    """
    band, sitting = game.band, game.council
    if band is None or sitting is None or SEAT not in game.asking:
        return None
    params, date = game.params, game.date
    counted = bands.census(params, band)
    wanted = decisions.needs(params, band)
    leader = sitting['leader']
    laid = [
        Option(
            at,
            dict(entry['proposal']),
            entry['key'],
            entry['votes'],
            entry['proposal'] == leader,
            entry['score'],
            _ground(game, band, entry['proposal'], wanted),
        )
        for at, entry in enumerate(sitting['table'], start=1)
    ]
    abstaining = {'kind': ABSTAIN}
    laid.append(Option(len(laid) + 1, abstaining, council.key(abstaining), 0, False, 0.0, None))
    resources = params.resources
    return Observation(
        year=date.year,
        month=date.month,
        day=date.day,
        part=date.part,
        season=date.season,
        people=dict(counted.counts),
        pregnant=counted.pregnant,
        injured=counted.injured,
        sick=counted.sick,
        states=tuple(band.states),
        fatigue=band.fatigue,
        food_days=bands.held_days(params, band, FOOD),
        water_days=bands.held_days(params, band, WATER),
        hunger=wanted[decisions.HUNGER],
        thirst=wanted[bands.THIRST],
        skills=tuple(band.lore[lore.KNOWN]),
        goods={name: band.stores.held(name) for name, held in resources.items() if held.kind == GOODS},
        kits={
            name: sum(member.kit.held(name) > 0 for member in band.members)
            for name, held in resources.items()
            if held.held == PERSONAL
        },
        status=game.status,
        voice=sitting['voice'],
        occasion=sitting.get('occasion'),
        sight=params.units.band.sight,
        winter_left=_winter_left(params, game.day),
        options=tuple(laid),
    )


def _ground(game: Game, band: Band, proposal: dict[str, Any], wanted: dict[str, float]) -> Ground:
    params, era = game.params, game.era
    to = band.place if proposal['kind'] != GO else council.target(proposal)
    cell = decisions.seen(params, band, to, era)
    held = decisions.expected(params, band) if cell is None else cell
    route: int | None = 0
    if to != band.place:
        way = routes.lay(params, band, to, game.inside, partial(decisions.looks, params, band, era), wanted)
        route = None if way is None else len(way)
    return Ground(
        biome=None if cell is None else cell['biome'],
        food=held.get(FOOD, 0.0),
        water=held.get(WATER, 0.0),
        threat=held.get(THREAT, 0.0),
        passability=held.get(PASSABILITY, 0.0),
        river=bool(cell and cell.get('river')),
        unknown=cell is None,
        route=route,
    )


def _winter_left(params: Params, day: int) -> float:
    """
    The share of the run of seasons that offer a winter camp still to come, 1 before it begins.
    """
    per_year = params.time.days_per_year
    today = day % per_year + 1
    starts = SeasonSchedule(params.time, 1).starts
    offered = params.units.band.winter_camp.offered.seasons
    at = max(index for index, (_, start) in enumerate(starts) if start <= today)
    if starts[at][0] not in offered:
        return 1.0
    first, last = at, at
    while first > 0 and starts[first - 1][0] in offered:
        first -= 1
    while last + 1 < len(starts) and starts[last + 1][0] in offered:
        last += 1
    begun = starts[first][1]
    ends = starts[last + 1][1] if last + 1 < len(starts) else per_year + 1
    return (ends - today) / (ends - begun)


def _calm(seen: Observation) -> float:
    return 1.0 - max(seen.hunger, seen.thirst)


def _lacks(seen: Observation, option: Option) -> float:
    leader = seen.leader
    if option.leads or option.ground is None or leader is None or leader.votes <= 0:
        return 0.0
    return max(leader.votes - option.votes - seen.voice, 0.0) / leader.votes


def _far(seen: Observation, option: Option) -> float:
    if option.ground is None or option.ground.route is None:
        return 0.0
    return option.ground.route / max(seen.sight, 1)


def _on(prop: str, option: Option) -> float:
    return 0.0 if option.ground is None else float(getattr(option.ground, prop))


type Feature = Callable[[Observation, Option], float]

# Every name of content.FEATURES, as docs/lab/players.md tells them.
MEASURES: dict[str, Feature] = {
    'go': lambda seen, option: float(option.kind == GO),
    'stay': lambda seen, option: float(option.kind == STAY),
    'winter': lambda seen, option: float(option.kind == WINTER),
    'abstain': lambda seen, option: float(option.kind == ABSTAIN),
    'votes': lambda seen, option: option.votes / max(sum(held.votes for held in seen.options), 1),
    'leader': lambda seen, option: float(option.leads),
    'score': lambda seen, option: option.score,
    'hunger_food': lambda seen, option: seen.hunger * _on(FOOD, option),
    'thirst_water': lambda seen, option: seen.thirst * _on(WATER, option),
    'calm_threat': lambda seen, option: _calm(seen) * _on(THREAT, option),
    'river': lambda seen, option: _on('river', option),
    'unknown': lambda seen, option: _on('unknown', option),
    'distance': _far,
    'winter_short': lambda seen, option: seen.winter_left if option.kind == WINTER else 0.0,
    'short_stay': lambda seen, option: float(option.kind == STAY and min(seen.food_days, seen.water_days) < 1.0),
    'outvoted': _lacks,
}


def features(seen: Observation, option: Option, names: tuple[str, ...] = FEATURES) -> list[float]:
    return [MEASURES[name](seen, option) for name in names]


def scores(mind: Mind, seen: Observation) -> list[float]:
    """
    A mind's score of every option: the sum of its weights times its features.
    """
    return [
        sum(weight * value for weight, value in zip(mind.weights, features(seen, option, mind.features), strict=True))
        for option in seen.options
    ]


def choose(mind: Mind, seen: Observation) -> int:
    """
    The number of the option a mind scores best, the first of the table on a tie.
    """
    scored = scores(mind, seen)
    best = max(range(len(scored)), key=lambda at: (scored[at], -at))
    return seen.options[best].number
