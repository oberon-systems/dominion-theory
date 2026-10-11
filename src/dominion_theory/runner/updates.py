"""
What leaves a runner: updates in order, the answer to a subscriber that fell behind, the end.
"""

from dataclasses import asdict, dataclass
from typing import Any

from ..engine import Date, Event


@dataclass(frozen=True)
class Update:
    """
    Not a tick: nothing here says how many steps of the engine it covers.
    """

    seq: int
    date: Date
    events: list[Event]
    changes: dict[str, Any]
    waiting: list[str]

    def data(self) -> dict[str, Any]:
        return {
            'seq': self.seq,
            'date': asdict(self.date),
            'events': [event.data() for event in self.events],
            'changes': self.changes,
            'waiting': list(self.waiting),
        }


@dataclass(frozen=True)
class Resync:
    seq: int

    def data(self) -> dict[str, Any]:
        return {'resync': True, 'seq': self.seq}


@dataclass(frozen=True)
class Ended:
    outcome: str
    tick: int
    hash: str
