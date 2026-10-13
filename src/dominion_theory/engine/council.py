"""
The council: the vote, the judgement and status, as docs/game/indirect_control.md states them.
"""

from collections.abc import Mapping
from typing import Any

from ..content import Duration, Params
from . import decisions
from .band import DIRECTIONS, ENCOUNTER, GATHER, Band, camp, moving
from .commands import MOVE, PROPOSALS, REST, STAY
from .events import PROPOSAL

WORKED = 'worked'
FAILED = 'failed'
DISASTER = 'disaster'
# The name a proposal has among the entries of council.intent and council.status.
NAMES = {MOVE: 'move', REST: 'rest', STAY: 'stay_and_gather'}
STATUS = {MOVE: 'move', STAY: 'stay'}
HIGHEST = 100.0


type Proposal = dict[str, Any]


def proposal(fields: Mapping[str, Any]) -> Proposal | None:
    """
    The proposal of a call-council, or None when the rules know no such proposal.
    """
    held = fields.get('proposal')
    if set(fields) != {'proposal'} or not isinstance(held, Mapping):
        return None
    kind = held.get('kind')
    if not isinstance(kind, str) or kind not in PROPOSALS or set(held) != {'kind', *PROPOSALS[kind]}:
        return None
    if kind == MOVE and held['towards'] not in DIRECTIONS:
        return None
    return dict(held)


def key(proposal: Proposal) -> str:
    return f'{PROPOSAL}{proposal["kind"]}' + (f'-{proposal["towards"]}' if proposal['kind'] == MOVE else '')


def scores(params: Params, band: Band, proposal: Proposal, part: str, era: str) -> tuple[float, float]:
    """
    What the decision function gives the first action of a proposal, and the band's own best.
    """
    found = decisions.options(params, band, part, era)
    best = max(held.score for held in found)
    if proposal['kind'] == MOVE:
        towards = decisions.way(params, band, proposal['towards'], era)
        wanted = [moving(towards)] if towards is not None else []
    elif proposal['kind'] == STAY:
        wanted = [held.action for held in found if held.action['kind'] == GATHER] or [camp()]
    else:
        wanted = [camp()]
    given = [held.score for held in found if held.action in wanted]
    return (max(given) if given else min(held.score for held in found)), best


def agreement(proposed: float, best: float) -> float:
    if proposed >= best:
        return 1.0
    if best <= 0:
        return 0.0
    return min(max(proposed / best, 0.0), 1.0)


def voice(params: Params, population: int, status: float) -> float:
    held = params.council.voice
    return max(held.least, held.share * population * status / HIGHEST)


def vote(params: Params, band: Band, proposal: Proposal, status: float, part: str, era: str) -> tuple[float, float]:
    """
    The voices for the proposal and all the voices; it passes when the first is above half the second.
    """
    others = band.population - 1
    spoken = voice(params, band.population, status)
    return agreement(*scores(params, band, proposal, part, era)) * others + spoken, others + spoken


def intent(params: Params, proposal: Proposal) -> Duration:
    """
    How long the band holds a proposal that passed, as a duration of the tree.
    """
    kept: Duration = getattr(params.council.intent, NAMES[proposal['kind']])
    return kept


def window(params: Params, proposal: Proposal) -> Duration:
    """
    How long after the call a proposal is judged, as a duration of the tree.
    """
    return params.council.judgement.move_after if proposal['kind'] == MOVE else intent(params, proposal)


def supply(params: Params, band: Band) -> float:
    """
    The lesser of the days of food and of water in the stores, held at the cap of the judgement.
    """
    cap = params.parts(params.council.judgement.supply_cap) / params.time.parts_per_day
    return min(cap, *(decisions.held_days(params, band, prop) for prop in decisions.NEEDS))


def verdict(params: Params, judgement: dict[str, Any], now: float) -> str:
    """
    How a proposal ended, from the band at the call kept in the judgement and its supply now.
    """
    rules = params.council.judgement
    kind, lost = judgement['proposal']['kind'], judgement['lost']
    died = sum(lost.values())
    if kind == REST or (kind == STAY and not lost.get(ENCOUNTER)):
        return WORKED
    if died / judgement['population'] >= rules.disaster:
        return DISASTER
    if kind == STAY or died or now < judgement['supply'] - rules.tolerance:
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
