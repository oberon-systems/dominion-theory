"""
The players of the seat besides a person: each answers the council it is shown with the number of an option or 0
for silence, and the seat turns the answer into a vote: docs/lab/players.md.
"""

from collections.abc import Callable, Mapping
from typing import Any, Protocol

import numpy as np

from ..content import Mind, Params
from ..engine import Command, Game, Observation, Vote, observe
from ..engine.observation import SEAT, choose
from ..engine.streams import Streams

SILENCE = 0
# A stream of the player's own, apart from the game's, so that a replay without the player draws the same.
STREAM = 'player'


class Player(Protocol):
    name: str

    def answer(self, seen: Observation) -> int: ...


class Leader:
    """
    Backs the option that leads, which costs nothing and turns nothing.
    """

    name = 'leader'

    def answer(self, seen: Observation) -> int:
        leader = seen.leader
        return SILENCE if leader is None else leader.number


class Silent:
    name = 'silent'

    def answer(self, seen: Observation) -> int:
        return SILENCE


class Random:
    """
    An option drawn from a stream of its own, silence among them.
    """

    name = 'random'

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    @classmethod
    def drawn(cls, seed: int, draw: int) -> Random:
        return cls(Streams(seed, draw=draw)[STREAM])

    def answer(self, seen: Observation) -> int:
        return int(self.rng.integers(len(seen.options) + 1))


class Greedy:
    """
    The option the band itself scores best, the first of the table on a tie; it never abstains.
    """

    name = 'greedy'

    def answer(self, seen: Observation) -> int:
        offered = [option for option in seen.options if option.ground is not None]
        if not offered:
            return SILENCE
        return max(offered, key=lambda option: (option.score, -option.number)).number


class Minded:
    """
    A mind of the tree in the seat.
    """

    def __init__(self, name: str, mind: Mind) -> None:
        self.name = name
        self.mind = mind

    def answer(self, seen: Observation) -> int:
        return choose(self.mind, seen)


SCRIPTED: dict[str, Callable[[], Player]] = {'leader': Leader, 'silent': Silent, 'greedy': Greedy}


def made(spec: str | Mapping[str, Any], params: Params, seed: int, draw: int = 0) -> Player:
    """
    A player by its name, or a mind of the tree by {mind: name}; the random one draws from the seed and draw given.
    """
    if isinstance(spec, Mapping):
        name = str(spec.get('mind'))
        if set(spec) != {'mind'} or name not in params.minds:
            raise ValueError(f'a mind of {", ".join(params.minds)}, not {dict(spec)}')
        return Minded(name, params.minds[name])
    if spec == Random.name:
        return Random.drawn(seed, draw)
    if spec not in SCRIPTED:
        raise ValueError(f'one of {", ".join([*SCRIPTED, Random.name])} or a mind, not {spec}')
    return SCRIPTED[spec]()


def vote(seen: Observation, number: int, seat: str = SEAT) -> Vote | None:
    """
    The vote of an answer; an answer that names no option is silence.
    """
    option = next((held for held in seen.options if held.number == number), None)
    return None if option is None else Vote(seat, dict(option.proposal))


def sit(game: Game, player: Player, submit: Callable[[Command], None] | None = None) -> tuple[int, Vote | None] | None:
    """
    Asks the player while the council of the day waits for the seat and submits its vote, to the game or by the
    submit given, as a runner does: the answer and the vote, None when no council waits.
    """
    seen = observe(game)
    if seen is None:
        return None
    number = player.answer(seen)
    given = vote(seen, number)
    if given is not None:
        (submit or game.submit)(given)
    return number, given
