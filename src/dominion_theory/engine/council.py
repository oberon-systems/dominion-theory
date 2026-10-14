"""
The council of the day: the table, the decision, the judgement and status, as docs/game/indirect_control.md
states them.
"""

import math
from collections.abc import Mapping
from typing import Any

from ..content import Params
from . import decisions
from .band import DIRECTIONS, ENCOUNTER, GATHER, Band, camp, moving
from .commands import ABSTAIN, MOVE, PROPOSALS, REST, STAY
from .decisions import Scored
from .events import NO_LEADER, PROPOSAL

WORKED = 'worked'
FAILED = 'failed'
DISASTER = 'disaster'
STATUS = {MOVE: 'move', STAY: 'stay'}
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


def score(params: Params, band: Band, found: list[Scored], proposal: Proposal, era: str) -> float:
    """
    What the decision function gives the first action a proposal leads to.
    """
    if proposal['kind'] == MOVE:
        towards = decisions.way(params, band, proposal['towards'], era)
        wanted = [moving(towards)] if towards is not None else []
    elif proposal['kind'] == STAY:
        wanted = [held.action for held in found if held.action['kind'] == GATHER] or [camp()]
    else:
        wanted = [camp()]
    given = [held.score for held in found if held.action in wanted]
    return max(given) if given else min(held.score for held in found)


def votes(scores: list[float], members: int) -> list[int]:
    """
    Whole votes in proportion to the scores above zero, by the largest remainder, ties to the earlier score.
    """
    total = sum(held for held in scores if held > 0)
    if total <= 0:
        return [0] * len(scores)
    exact = [max(held, 0.0) / total * members for held in scores]
    whole = [math.floor(share) for share in exact]
    for index in sorted(range(len(exact)), key=lambda at: (whole[at] - exact[at], at))[: members - sum(whole)]:
        whole[index] += 1
    return whole


def table(params: Params, band: Band, part: str, era: str) -> Table:
    """
    How the others' votes lie over the options the band can take; options without a vote are left out.
    """
    found = decisions.options(params, band, part, era)
    offered = [
        proposal
        for proposal in OPTIONS
        if proposal['kind'] != MOVE or decisions.way(params, band, proposal['towards'], era) == proposal['towards']
    ]
    scores = [score(params, band, found, proposal, era) for proposal in offered]
    laid = [
        {'proposal': proposal, 'votes': given}
        for proposal, given in zip(offered, votes(scores, band.population - 1), strict=True)
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
