"""
What a game played from its seat came to, counted from the updates of its runner: the line of docs/lab/metrics.md
but which game it was, its outcome and its time.
"""

from collections import Counter
from typing import Any

from ..engine import Game
from ..engine import council as councils
from ..engine.events import (
    COUNCIL_ABSTAINED,
    COUNCIL_AGREED,
    COUNCIL_FOLLOWED,
    COUNCIL_OPENED,
    COUNCIL_OUTVOTED,
    COUNCIL_TURNED,
    PEOPLE_BORN,
    PEOPLE_LOST,
    PROPOSAL_EVEN,
    PROPOSAL_FAILED,
    PROPOSAL_WORKED,
    SKILL,
    SKILL_LEARNED,
)
from ..engine.game import BANISHED, DIED
from .updates import Ended, Update

REACHED = 'reached'
CAP = 'cap'
OUTCOMES = (REACHED, DIED, BANISHED, CAP)

COUNCILS = {
    COUNCIL_OPENED: 'sat',
    COUNCIL_AGREED: 'settled',
    COUNCIL_FOLLOWED: 'backed',
    COUNCIL_TURNED: 'turned',
    COUNCIL_OUTVOTED: 'outvoted',
    COUNCIL_ABSTAINED: 'abstained',
}
VERDICTS = {PROPOSAL_WORKED: 'worked', PROPOSAL_EVEN: 'even', PROPOSAL_FAILED: 'failed'}


class Tally:
    """
    Listens to a runner and counts its game from the first tick on.
    """

    def __init__(self, game: Game) -> None:
        self.game = game
        self.start = self.most = self.people
        self.lowest = game.status
        self.born = 0
        self.died: Counter[str] = Counter()
        self.councils: Counter[str] = Counter(dict.fromkeys(COUNCILS.values(), 0))
        self.verdicts: Counter[str] = Counter(dict.fromkeys(VERDICTS.values(), 0))
        self.occasions: Counter[str] = Counter()
        self.skills: dict[str, int] = {}

    @property
    def people(self) -> int:
        return 0 if self.game.band is None else self.game.band.population

    @property
    def day(self) -> int:
        return self.game.clock.parts // self.game.params.time.parts_per_day

    def heard(self, message: Update | Ended) -> None:
        if isinstance(message, Ended):
            return
        game = self.game
        self.most = max(self.most, self.people)
        self.lowest = min(self.lowest, game.status)
        for event in message.events:
            values = event.values
            if event.key in COUNCILS:
                self.councils[COUNCILS[event.key]] += 1
            if event.key in (COUNCIL_OPENED, COUNCIL_AGREED):
                self.occasions[str(values['occasion']).removeprefix(councils.OCCASION)] += 1
            elif event.key in VERDICTS:
                self.verdicts[VERDICTS[event.key]] += 1
            elif event.key == PEOPLE_BORN:
                self.born += values['count']
            elif event.key == PEOPLE_LOST:
                self.died[values['cause']] += values['count']
            elif event.key == SKILL_LEARNED:
                per_day = game.params.time.parts_per_day
                self.skills[str(values['skill']).removeprefix(SKILL)] = (game.clock.parts - 1) // per_day

    def data(self) -> dict[str, Any]:
        return {
            'day': self.day,
            'people': {'start': self.start, 'end': self.people, 'most': self.most},
            'born': self.born,
            'died': sum(self.died.values()),
            'causes': dict(sorted(self.died.items())),
            'councils': dict(self.councils),
            'occasions': dict(sorted(self.occasions.items())),
            'verdicts': dict(self.verdicts),
            'status': {'end': round(self.game.status, 2), 'lowest': round(self.lowest, 2)},
            'skills': self.skills,
        }
