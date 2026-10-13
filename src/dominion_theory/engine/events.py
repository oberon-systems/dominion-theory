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
BAND_DIED = 'band-died'
ENCOUNTER = 'encounter'
COUNCIL_ACCEPTED = 'council-accepted'
COUNCIL_DECLINED = 'council-declined'
PROPOSAL_WORKED = 'proposal-worked'
PROPOSAL_FAILED = 'proposal-failed'
PROPOSAL_DISASTER = 'proposal-disaster'
INTENT_ENDED = 'intent-ended'
SEAT_BANISHED = 'seat-banished'

REFUSED_UNKNOWN_COMMAND = 'refused-unknown-command'
REFUSED_UNKNOWN_SEAT = 'refused-unknown-seat'
REFUSED_COUNCIL_TOO_SOON = 'refused-council-too-soon'
REFUSED_PROPOSAL_PENDING = 'refused-proposal-pending'
REFUSED_NO_SUCH_DIRECTION = 'refused-no-such-direction'
REFUSED_SEAT_BANISHED = 'refused-seat-banished'

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
    BAND_DIED: (),
    ENCOUNTER: ('kind', 'lost'),
    COUNCIL_ACCEPTED: ('proposal', 'yes', 'all'),
    COUNCIL_DECLINED: ('proposal', 'yes', 'all', 'status'),
    PROPOSAL_WORKED: ('proposal', 'status'),
    PROPOSAL_FAILED: ('proposal', 'lost', 'status'),
    PROPOSAL_DISASTER: ('proposal', 'lost', 'status'),
    INTENT_ENDED: ('proposal',),
    SEAT_BANISHED: (),
}

REASONS: tuple[str, ...] = (
    REFUSED_UNKNOWN_COMMAND,
    REFUSED_UNKNOWN_SEAT,
    REFUSED_COUNCIL_TOO_SOON,
    REFUSED_PROPOSAL_PENDING,
    REFUSED_NO_SUCH_DIRECTION,
    REFUSED_SEAT_BANISHED,
)
STATE = 'state-'
KIND = 'encounter-'
PROPOSAL = 'proposal-'


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
