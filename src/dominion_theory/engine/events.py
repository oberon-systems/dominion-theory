"""
What the engine reports: a message key with values, never text. Every key is declared here.
"""

from dataclasses import dataclass
from typing import Any

from .clock import DAY_STARTED, MONTH_STARTED, SEASON_STARTED, YEAR_STARTED

COMMAND_ACCEPTED = 'command-accepted'
COMMAND_REFUSED = 'command-refused'

BAND_STATE_BEGAN = 'band-state-began'
BAND_STATE_ENDED = 'band-state-ended'
PEOPLE_LOST = 'people-lost'
PEOPLE_BORN = 'people-born'
PEOPLE_INJURED = 'people-injured'
BAND_DIED = 'band-died'
ENCOUNTER = 'encounter'
COUNCIL_OPENED = 'council-opened'
COUNCIL_AGREED = 'council-agreed'
COUNCIL_FOLLOWED = 'council-followed'
COUNCIL_TURNED = 'council-turned'
COUNCIL_OUTVOTED = 'council-outvoted'
COUNCIL_ABSTAINED = 'council-abstained'
PROPOSAL_WORKED = 'proposal-worked'
PROPOSAL_EVEN = 'proposal-even'
PROPOSAL_FAILED = 'proposal-failed'
INTENT_ENDED = 'intent-ended'
INTENT_ARRIVED = 'intent-arrived'
SEAT_BLAMED = 'seat-blamed'
SEAT_PRAISED = 'seat-praised'
SEAT_BANISHED = 'seat-banished'
SKILL_LEARNED = 'skill-learned'
GOODS_MADE = 'goods-made'
GOODS_SPOILED = 'goods-spoiled'
GOODS_WORN = 'goods-worn'

REFUSED_UNKNOWN_COMMAND = 'refused-unknown-command'
REFUSED_UNKNOWN_SEAT = 'refused-unknown-seat'
REFUSED_NO_COUNCIL = 'refused-no-council'
REFUSED_ALREADY_VOTED = 'refused-already-voted'
REFUSED_NO_SUCH_PLACE = 'refused-no-such-place'
REFUSED_SEAT_BANISHED = 'refused-seat-banished'
REFUSED_OUT_OF_SEASON = 'refused-out-of-season'
REFUSED_NOT_LEARNED = 'refused-not-learned'

EVENTS: dict[str, tuple[str, ...]] = {
    COMMAND_ACCEPTED: ('id',),
    COMMAND_REFUSED: ('id', 'reason'),
    DAY_STARTED: ('year', 'month', 'day'),
    MONTH_STARTED: ('year', 'month', 'season'),
    SEASON_STARTED: ('year', 'season'),
    YEAR_STARTED: ('year', 'seasons'),
    BAND_STATE_BEGAN: ('state',),
    BAND_STATE_ENDED: ('state',),
    PEOPLE_LOST: ('count', 'cause'),
    PEOPLE_BORN: ('count',),
    PEOPLE_INJURED: ('count',),
    BAND_DIED: (),
    ENCOUNTER: ('kind', 'lost'),
    COUNCIL_OPENED: ('leader', 'occasion'),
    COUNCIL_AGREED: ('leader', 'occasion'),
    COUNCIL_FOLLOWED: ('proposal',),
    COUNCIL_TURNED: ('proposal', 'yes', 'all'),
    COUNCIL_OUTVOTED: ('proposal', 'winner', 'status'),
    COUNCIL_ABSTAINED: ('status',),
    PROPOSAL_WORKED: ('proposal', 'status'),
    PROPOSAL_EVEN: ('proposal', 'status'),
    PROPOSAL_FAILED: ('proposal', 'status'),
    INTENT_ENDED: ('proposal',),
    INTENT_ARRIVED: (),
    SEAT_BLAMED: ('lost', 'status'),
    SEAT_PRAISED: ('born', 'status'),
    SEAT_BANISHED: (),
    SKILL_LEARNED: ('skill',),
    GOODS_MADE: ('resource', 'count'),
    GOODS_SPOILED: ('resource', 'count'),
    GOODS_WORN: ('resource', 'count'),
}

REASONS: tuple[str, ...] = (
    REFUSED_UNKNOWN_COMMAND,
    REFUSED_UNKNOWN_SEAT,
    REFUSED_NO_COUNCIL,
    REFUSED_ALREADY_VOTED,
    REFUSED_NO_SUCH_PLACE,
    REFUSED_SEAT_BANISHED,
    REFUSED_OUT_OF_SEASON,
    REFUSED_NOT_LEARNED,
)
STATE = 'state-'
KIND = 'encounter-'
SKILL = 'skill-'
PROPOSAL = 'proposal-'
NO_LEADER = 'proposal-none'


@dataclass(frozen=True)
class Event:
    key: str
    values: dict[str, Any]

    def __post_init__(self) -> None:
        if self.key not in EVENTS:
            raise ValueError(f'the event {self.key} is not declared')
        if set(self.values) != set(EVENTS[self.key]):
            raise ValueError(f'the event {self.key} carries {", ".join(EVENTS[self.key])}')

    def data(self) -> dict[str, Any]:
        return {'key': self.key, 'values': dict(self.values)}
