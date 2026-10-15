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
from .band import DIRECTIONS, ENCOUNTER, Band
from .commands import ABSTAIN, MOVE, PROPOSALS, REST, STAY
from .events import NO_LEADER, PROPOSAL

WORKED = 'worked'
FAILED = 'failed'
DISASTER = 'disaster'
STATUS = {MOVE: 'move', STAY: 'stay'}
STAYING = {'kind': STAY}
RESTING = {'kind': REST}
HIGHEST = 100.0
# The fixed order of the options, the one of the decision function: the camp, the gatherings, the moves.
OPTIONS: tuple[dict[str, Any], ...] = (
    {'kind': REST},
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


def score(params: Params, band: Band, part: str, era: str) -> dict[str, float]:
    """
    What a day of every proposal is worth to the band, by key: staying on the land it stands on, resting
    there without gathering, or walking to the best land that way.
    """
    weights = params.units.band.decisions.weights
    wanted = decisions.needs(params, band, part)
    own = band.known.get(band.place)
    here = decisions.worth(params, own, wanted)[0] if own else 0.0
    gain = sum(wanted[need] * own.get(prop, 0.0) for prop, (need, _) in decisions.NEEDS.items()) if own else 0.0
    found = {
        key(STAYING): weights.move * here,
        key(RESTING): weights.move * (here - gain) + weights.rest * wanted[decisions.REST],
    }
    for held in decisions.options(params, band, part, era, allowed={bands.MOVE}, walking=True):
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


def table(params: Params, band: Band, part: str, era: str) -> Table:
    """
    How the others' votes lie over the options the band can take; options without a vote are left out.
    """
    days = score(params, band, part, era)
    offered = [proposal for proposal in OPTIONS if key(proposal) in days]
    scores = [days[key(proposal)] for proposal in offered]
    laid = [
        {'proposal': proposal, 'votes': given}
        for proposal, given in zip(offered, votes(scores, band.population - 1, params.council.spread), strict=True)
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
    votes = {key(entry['proposal']): float(entry['votes']) for entry in laid}
    named = key(proposal)
    votes[named] = votes.get(named, 0.0) + spoken
    order = [key(option) for option in OPTIONS]
    best = max(votes, key=lambda name: (votes[name], name == named, -order.index(name)))
    winner = proposal if best == named else next(entry['proposal'] for entry in laid if key(entry['proposal']) == best)
    return dict(winner), votes[named]


def voice(params: Params, population: int, status: float) -> float:
    held = params.council.voice
    return max(held.least, held.share * population * status / HIGHEST)


def worth(params: Params, band: Band, wanted: dict[str, float]) -> float:
    """
    What the cell the band stands on is worth to it, weighed by the needs given.
    """
    cell = band.known.get(band.place)
    return decisions.worth(params, cell, wanted)[0] if cell else 0.0


def verdict(params: Params, judgement: dict[str, Any], now: float) -> str:
    """
    How a proposal ended, from the band at the decision kept in the judgement and the worth of its cell now.
    """
    kind, lost = judgement['proposal']['kind'], judgement['lost']
    died = sum(lost.values())
    if kind == REST or (kind == STAY and not lost.get(ENCOUNTER)):
        return WORKED
    if died / judgement['population'] >= params.council.judgement.disaster:
        return DISASTER
    if kind == STAY or died or now < judgement['worth']:
        return FAILED
    return WORKED


def amount(params: Params, proposal: Proposal, found: str) -> float:
    """
    What a verdict does to status.
    """
    name = 'rest' if proposal['kind'] == REST else f'{STATUS[proposal["kind"]]}_{found}'
    moved: float = getattr(params.council.status, name)
    return moved


def held(status: float) -> float:
    return min(max(status, 0.0), HIGHEST)
