"""
The council of the day: the table, the decision, the judgement and status, as docs/game/indirect_control.md
states them.
"""

import math
from collections.abc import Mapping
from typing import Any

from ..content import Params
from . import band as bands
from . import decisions
from .band import DIRECTIONS, Band, voters
from .commands import ABSTAIN, MOVE, PROPOSALS, STAY
from .events import NO_LEADER, PROPOSAL

WORKED = 'worked'
FAILED = 'failed'
DISASTER = 'disaster'
STATUS = {MOVE: 'move', STAY: 'stay'}
STAYING = {'kind': STAY}
HIGHEST = 100.0
OCCASION = 'occasion-'
# What calls a council, in the order the first that holds is named: docs/game/indirect_control.md, Occasions.
FIRST = 'first'
DEATH = 'death'
HUNGER = 'hunger'
CLOSED = 'closed'
RESTLESS = 'restless'
SEASON = 'season'
RIVER = 'river'
OCCASIONS = (FIRST, DEATH, HUNGER, CLOSED, RESTLESS, SEASON, RIVER)
# The fixed order of the options, the one of the decision function: the gatherings, the moves.
OPTIONS: tuple[dict[str, Any], ...] = (
    {'kind': STAY},
    *({'kind': MOVE, 'towards': name} for name in DIRECTIONS),
)


type Proposal = dict[str, Any]
type Table = list[dict[str, Any]]


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
    if kind == MOVE and held['towards'] not in DIRECTIONS:
        return None
    return dict(held)


def key(proposal: Proposal | None) -> str:
    if proposal is None:
        return NO_LEADER
    return f'{PROPOSAL}{proposal["kind"]}' + (f'-{proposal["towards"]}' if proposal['kind'] == MOVE else '')


def score(params: Params, band: Band, era: str) -> dict[str, float]:
    """
    What a day of every proposal is worth to the band, by key: staying on the land it stands on or walking to
    the best land that way.
    """
    weights = params.units.band.decisions.weights
    wanted = decisions.needs(params, band)
    own = band.known.get(band.place)
    here = decisions.worth(params, own, wanted)[0] if own else 0.0
    found = {key(STAYING): weights.move * here}
    for held in decisions.options(params, band, era, allowed={bands.MOVE}, walking=True):
        found[key({'kind': MOVE, 'towards': held.action['towards']})] = held.score + weights.move * here
    return found


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


def table(params: Params, band: Band, era: str) -> Table:
    """
    How the others' votes lie over the options the band can take; options without a vote are left out.
    """
    days = score(params, band, era)
    offered = [proposal for proposal in OPTIONS if key(proposal) in days]
    scores = [days[key(proposal)] for proposal in offered]
    given = votes(scores, voters(params, band) - 1, params.council.spread)
    laid = [{'proposal': proposal, 'votes': held} for proposal, held in zip(offered, given, strict=True)]
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
    votes = {key(entry['proposal']): float(entry['votes']) for entry in laid}
    named = key(proposal)
    votes[named] = votes.get(named, 0.0) + spoken
    order = [key(option) for option in OPTIONS]
    best = max(votes, key=lambda name: (votes[name], name == named, -order.index(name)))
    winner = proposal if best == named else next(entry['proposal'] for entry in laid if key(entry['proposal']) == best)
    return dict(winner), votes[named]


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


def worth(params: Params, band: Band, wanted: dict[str, float]) -> float:
    """
    What the cell the band stands on is worth to it, weighed by the needs given.
    """
    cell = band.known.get(band.place)
    return decisions.worth(params, cell, wanted)[0] if cell else 0.0


def expected(params: Params, band: Band, era: str, leader: Proposal | None) -> float:
    """
    The day the leader promised, or staying when nobody voted.
    """
    days = score(params, band, era)
    return days.get(key(leader), days[key(STAYING)])


def reached(params: Params, band: Band, wanted: dict[str, float]) -> float:
    return params.units.band.decisions.weights.move * worth(params, band, wanted)


def verdict(params: Params, judgement: dict[str, Any], now: float) -> str:
    """
    How a proposal ended: lives lost first, then the day reached against the day the leader promised.
    """
    died = sum(judgement['lost'].values())
    if died / judgement['population'] >= params.council.judgement.disaster:
        return DISASTER
    if died:
        return FAILED
    return WORKED if now >= judgement['expected'] else FAILED


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
    votes = {key(entry['proposal']): entry['votes'] for entry in laid}
    return bool(laid) and 2 * votes.get(key(standing), 0) < max(votes.values())


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
