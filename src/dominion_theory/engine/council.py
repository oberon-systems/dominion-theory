"""
The council of the day: the table, the decision, the judgement and status, as docs/game/indirect_control.md
states them.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import Any

from ..content import Params
from . import band as bands
from . import decisions, routes
from .band import Band, voters
from .cells import Place
from .clock import SeasonSchedule
from .commands import ABSTAIN, GO, PROPOSALS, STAY, WINTER
from .events import NO_LEADER, PROPOSAL

UNKNOWN = 'unknown'
THROUGH = 'through-'

WORKED = 'worked'
EVEN = 'even'
FAILED = 'failed'
STATUS = {GO: 'go', STAY: 'stay', WINTER: 'camp'}
STAYING = {'kind': STAY}
WINTERING = {'kind': WINTER}
HIGHEST = 100.0
OCCASION = 'occasion-'
# What calls a council, in the order the first that holds is named: docs/game/indirect_control.md, Occasions.
FIRST = 'first'
DEATH = 'death'
ARRIVED = 'arrived'
HUNGER = 'hunger'
CLOSED = 'closed'
RESTLESS = 'restless'
SEASON = 'season'
RIVER = 'river'
OCCASIONS = (FIRST, DEATH, ARRIVED, HUNGER, CLOSED, RESTLESS, SEASON, RIVER)


type Proposal = dict[str, Any]
type Table = list[dict[str, Any]]
type Inside = Callable[[int, int], bool]


def answer(fields: Mapping[str, Any]) -> Proposal | None:
    """
    The proposal of a vote, abstaining included, or None when the rules know no such answer.
    """
    held = fields.get('proposal')
    if set(fields) != {'proposal'} or not isinstance(held, Mapping):
        return None
    kind = held.get('kind')
    if kind == ABSTAIN and set(held) == {'kind'}:
        return {'kind': ABSTAIN}
    if not isinstance(kind, str) or kind not in PROPOSALS or set(held) != {'kind', *PROPOSALS[kind]}:
        return None
    if kind == GO:
        to = held['to']
        if not isinstance(to, Mapping) or set(to) != {'x', 'y'} or not all(_whole(to[name]) for name in to):
            return None
        return going((to['x'], to['y']))
    return dict(held)


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def going(to: Place) -> Proposal:
    return {'kind': GO, 'to': {'x': to[0], 'y': to[1]}}


def target(proposal: Proposal) -> Place:
    return proposal['to']['x'], proposal['to']['y']


def key(proposal: Proposal | None, band: Band | None = None) -> str:
    """
    The words of a proposal: a go is told by the land of its target as the band knows it, when a band is given,
    and as going on through it when the band stands on the same land.
    """
    if proposal is None:
        return NO_LEADER
    if proposal['kind'] != GO:
        return f'{PROPOSAL}{proposal["kind"]}'
    to = target(proposal)
    if band is None or to == band.place:
        return f'{PROPOSAL}{GO}'
    cell, own = band.known.get(to), band.known.get(band.place)
    if cell is None:
        return f'{PROPOSAL}{GO}-{UNKNOWN}'
    through = own is not None and own['biome'] == cell['biome']
    return f'{PROPOSAL}{GO}-{THROUGH if through else ""}{cell["biome"]}'


def score(
    params: Params, band: Band, era: str, inside: Inside, extra: Sequence[Proposal] = (), wintering: bool = False
) -> list[tuple[Proposal, float]]:
    """
    What a day of every proposal is worth to the band, in the fixed order: staying on the land it stands on,
    a winter camp on it while one is offered, a go to the best land it knows each way clockwise from the north,
    a target named in the same way once, then every extra one it can reach. Staying in a built camp is worth
    its kept more.
    """
    weights = params.units.band.decisions.weights
    here = decisions.here(params, band, decisions.needs(params, band), era)
    kept = params.units.band.winter_camp.kept if bands.sheltered(band) else 0.0
    found: dict[Place | None, float] = {None: weights.move * (here + kept)}
    for held in decisions.options(params, band, era, allowed={bands.MOVE}, walking=True):
        to = held.pull
        if to is not None and inside(*to):
            found[to] = max(found.get(to, -math.inf), held.score + weights.move * here)
    for proposal in extra:
        if proposal['kind'] == GO and target(proposal) not in found:
            aimed = _aimed(params, band, era, inside, target(proposal))
            if aimed is not None:
                found[target(proposal)] = aimed
    days = [(STAYING if to is None else going(to), held) for to, held in found.items()]
    if wintering:
        days.insert(1, (WINTERING, weights.move * (decisions.wintering(params, band, era) + kept)))
    return days


def _aimed(params: Params, band: Band, era: str, inside: Inside, to: Place) -> float | None:
    """
    A day towards a target the band did not name itself, as it would weigh its own: the worth of the target
    by the length of the route; None when there is no route.
    """
    rules = params.units.band.decisions
    wanted = decisions.needs(params, band)
    cell = decisions.looks(params, band, era, to)
    way = routes.lay(params, band, to, inside, partial(decisions.looks, params, band, era), wanted)
    if cell is None or way is None:
        return None
    value = decisions.worth(params, cell, wanted, band.unease)[0]
    if value > 0:
        value = value / (1.0 + len(way) * rules.distance)
    elif to in band.known:
        value = value * (1.0 + len(way) * rules.distance)
    return rules.weights.move * value


def offered(params: Params, day: int) -> bool:
    """
    Whether a winter camp is offered on a day of the game: in one of its seasons, or in the days before one of
    them begins.
    """
    window = params.units.band.winter_camp.offered
    per_year = params.time.days_per_year
    schedule = SeasonSchedule(params.time, 1)
    today = day % per_year + 1
    if schedule.season(today) in window.seasons:
        return True
    before = params.days(window.before)
    return any(0 < (start - today) % per_year <= before for name, start in schedule.starts if name in window.seasons)


def votes(scores: list[float], members: int, spread: float) -> list[int]:
    """
    Whole votes by the weight exp(score / spread) of every option, by the largest remainder, ties to the earlier
    score.
    """
    if not scores:
        return []
    top = max(scores)
    weights = [math.exp((held - top) / spread) for held in scores]
    total = sum(weights)
    exact = [weight / total * members for weight in weights]
    whole = [math.floor(share) for share in exact]
    for index in sorted(range(len(exact)), key=lambda at: (whole[at] - exact[at], at))[: members - sum(whole)]:
        whole[index] += 1
    return whole


def table(
    params: Params, band: Band, era: str, inside: Inside, extra: Sequence[Proposal] = (), wintering: bool = False
) -> Table:
    """
    How the others' votes lie over the options the band can take, each with its words; options without a vote
    are left out.
    """
    days = score(params, band, era, inside, extra, wintering)
    given = votes([held for _, held in days], voters(params, band) - 1, params.council.spread)
    laid = [
        {'proposal': proposal, 'key': key(proposal, band), 'votes': held}
        for (proposal, _), held in zip(days, given, strict=True)
    ]
    return [entry for entry in laid if entry['votes']]


def leader(laid: Table) -> Proposal | None:
    """
    The option with the most votes of the others, the first in the fixed order of a tie.
    """
    if not laid:
        return None
    most = max(entry['votes'] for entry in laid)
    return next(dict(entry['proposal']) for entry in laid if entry['votes'] == most)


def decide(laid: Table, proposal: Proposal, spoken: float) -> tuple[Proposal, float]:
    """
    The winner once the player's voice is added to the proposal, and the votes of the proposal; a tie goes to
    the player, and among the others to the fixed order.
    """
    options = [(dict(entry['proposal']), float(entry['votes'])) for entry in laid]
    if all(option != proposal for option, _ in options):
        options.append((dict(proposal), 0.0))
    counted = [(option, held + spoken if option == proposal else held) for option, held in options]
    best = max(range(len(counted)), key=lambda at: (counted[at][1], counted[at][0] == proposal, -at))
    return counted[best][0], next(held for option, held in counted if option == proposal)


def settled(laid: Table, spoken: float) -> bool:
    """
    Whether the leader wins whatever the player says: no other option, one with no votes included, reaches its
    votes with the player's voice added.
    """
    if not laid:
        return False
    votes: list[int] = sorted((entry['votes'] for entry in laid), reverse=True)
    return (votes[1] if len(votes) > 1 else 0) + spoken < votes[0]


def voice(params: Params, voting: int, status: float) -> float:
    held = params.council.voice
    return max(held.least, held.share * voting * status / HIGHEST)


def worth(params: Params, band: Band, era: str, wanted: dict[str, float], unease: float) -> float:
    """
    What the cell the band stands on is worth to it, weighed by the needs and the unease given.
    """
    cell = decisions.seen(params, band, band.place, era)
    return decisions.worth(params, cell, wanted, unease)[0] if cell else 0.0


def expected(
    params: Params, band: Band, era: str, inside: Inside, leader: Proposal | None, wintering: bool = False
) -> float:
    """
    The day the leader promised, or staying when nobody voted.
    """
    days = score(params, band, era, inside, () if leader is None else (leader,), wintering)
    return next((held for proposal, held in days if proposal == leader), days[0][1])


def reached(params: Params, band: Band, era: str, wanted: dict[str, float], unease: float) -> float:
    return params.units.band.decisions.weights.move * worth(params, band, era, wanted, unease)


def verdict(params: Params, judgement: dict[str, Any], now: float) -> str:
    """
    How a proposal ended: the day reached against the day the leader promised, then against the land the band
    left. Deaths are no part of it: each is paid once, by whoever voted for the day.
    """
    if now >= judgement['expected']:
        return WORKED
    return EVEN if now >= judgement['before'] - params.council.judgement.slack else FAILED


def amount(params: Params, proposal: Proposal, found: str) -> float:
    """
    What a verdict does to status.
    """
    moved: float = getattr(params.council.status, f'{STATUS[proposal["kind"]]}_{found}')
    return moved


def restless(laid: Table, standing: Proposal | None) -> bool:
    """
    Whether the band wants another thing than the decision in force: it has fewer than half the votes of the
    leader, or there is none.
    """
    if standing is None:
        return True
    held = sum(entry['votes'] for entry in laid if entry['proposal'] == standing)
    return bool(laid) and 2 * held < max(entry['votes'] for entry in laid)


def scaled(amount: float, status: float) -> float:
    """
    A change of status as the height of status weighs it: above the middle gains shrink towards the top and
    losses grow; below it every amount is paid in full, so that a player can still fall to banishment.
    """
    middle = HIGHEST / 2
    if amount > 0:
        return amount * min((HIGHEST - status) / middle, 1.0)
    return amount * max(status / middle, 1.0)


def held(status: float) -> float:
    return min(max(status, 0.0), HIGHEST)
