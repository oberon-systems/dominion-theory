"""
What a seat asks of the game: the envelope of docs/api/commands.md and the kinds built so far.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

PASS = 'pass'  # noqa: S105
VOTE = 'vote'
ABSTAIN = 'abstain'
GO = 'go'
STAY = 'stay-and-gather'
WINTER = 'winter-camp'

BUILT = frozenset({PASS, VOTE})
ENVELOPE = ('id', 'kind')
# The fields of a proposal besides its kind.
PROPOSALS: dict[str, tuple[str, ...]] = {GO: ('to',), STAY: (), WINTER: ()}


@dataclass(frozen=True, kw_only=True)
class Command:
    """
    Any command. A kind the rules do not know is still a command, and is refused when judged.
    """

    seat: str
    kind: str
    id: str | None = None
    fields: Mapping[str, Any] = field(default_factory=dict)

    def envelope(self) -> dict[str, Any]:
        return {'id': self.id, 'kind': self.kind, **self.fields}

    def named(self, id: str) -> Command:
        return Command(seat=self.seat, kind=self.kind, id=id, fields=self.fields)

    @classmethod
    def read(cls, seat: str, envelope: Mapping[str, Any]) -> Command:
        fields = {name: value for name, value in envelope.items() if name not in ENVELOPE}
        return Command(seat=seat, kind=str(envelope.get('kind', '')), id=envelope.get('id'), fields=fields)


class Pass(Command):
    def __init__(self, seat: str, id: str | None = None) -> None:
        super().__init__(seat=seat, kind=PASS, id=id)


class Vote(Command):
    """
    The answer to the council of the day: a proposal, or {'kind': 'abstain'}.
    """

    def __init__(self, seat: str, proposal: Any, id: str | None = None) -> None:
        super().__init__(seat=seat, kind=VOTE, id=id, fields={'proposal': proposal})
