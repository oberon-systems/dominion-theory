"""
Playing a game as lines, for an input that is not a terminal: a coloured line per update, and every morning
the map and a numbered list of the council's options.
"""

from collections.abc import Callable, Iterator, Mapping
from typing import Any

import click

from ..i18n import render
from .api import Api
from .drawing import pictured
from .lines import (
    ABSTAIN,
    ANSWER,
    AWAY,
    LEADER,
    QUESTION,
    STATUS,
    UNCLEAR,
    VOTES,
    Look,
    Option,
    Part,
    options,
    parts,
)
from .session import Session

SILENCE = {'kind': 'abstain'}
STYLES: dict[Look, dict[str, Any]] = {
    Look.PLAIN: {},
    Look.DATE: {'dim': True},
    Look.BAND: {'fg': 'cyan'},
    Look.STATE: {'fg': 'red', 'bold': True},
    Look.STATUS: {'fg': 'yellow', 'bold': True},
    Look.EVENT: {},
    Look.COUNCIL: {'fg': 'magenta'},
    Look.LOSS: {'fg': 'red'},
}
NAMES: dict[str, Mapping[str, Any]] = {
    'stay': {'kind': 'stay-and-gather'},
    'stay-and-gather': {'kind': 'stay-and-gather'},
    'abstain': SILENCE,
}

type Proposal = Mapping[str, Any]
type Place = tuple[int, int]
type Choose = Callable[[list[Option], str, Place | None], Proposal]


def coloured(said: list[Part]) -> str:
    return ''.join(click.style(part.text, **STYLES[part.look]) for part in said)


def label(option: Option, lang: str) -> str:
    key = option.key
    text = render(VOTES, {'proposal': key, 'votes': option.votes}, lang) if option.votes else render(key, lang=lang)
    if option.far is not None:
        text = render(AWAY, {'option': text, 'cells': option.far}, lang)
    return render(LEADER, {'option': text}, lang) if option.leader else text


def understood(answer: str, listed: list[Option], place: Place | None = None) -> Proposal | None:
    """
    A number of the list, a name, or a point as two offsets from the band, x then y: '+3 -2'.
    """
    said = answer.strip().lower()
    if not said:
        return SILENCE
    if said.isdigit():
        number = int(said)
        if 1 <= number <= len(listed):
            return listed[number - 1].proposal
        return SILENCE if number == len(listed) + 1 else None
    offsets = said.split()
    if place is not None and len(offsets) == 2 and all(_offset(word) for word in offsets):
        dx, dy = (int(word) for word in offsets)
        return {'kind': 'go', 'to': {'x': place[0] + dx, 'y': place[1] + dy}}
    return NAMES.get(said)


def _offset(word: str) -> bool:
    return word.lstrip('+-').isdigit() and word.count('+') + word.count('-') <= 1


def prompted(listed: list[Option], lang: str, place: Place | None = None) -> Proposal:
    """
    The options as numbered lines, read back as a number, a name of the API or nothing at all.
    """
    click.echo(render(QUESTION, lang=lang))
    for number, option in enumerate(listed, 1):
        click.echo(f'{number}. {label(option, lang)}')
    click.echo(f'{len(listed) + 1}. {render(ABSTAIN, lang=lang)}')
    while True:
        answer = click.prompt(render(ANSWER, lang=lang), default='', show_default=False)
        chosen = understood(answer, listed, place)
        if chosen is not None:
            return chosen
        click.echo(render(UNCLEAR, {'answer': answer}, lang))


class Player:
    """
    A seat played as lines: it votes when the council of the day sits and passes otherwise.
    """

    def __init__(self, api: Api, game_id: str, lang: str, choose: Choose = prompted, debug: bool = False) -> None:
        self._session = Session(api, game_id)
        self._lang = lang
        self._choose = choose
        self._debug = debug

    def lines(self, limit: int | None = None) -> Iterator[str]:
        """
        The coloured lines of the game, at most limit updates of them; the map is drawn before every vote.
        """
        session = self._session
        yield from self._answer(session.seq)
        seen = 0
        for message in session.stream():
            if not message.get('resync'):
                yield coloured(parts(message, self._lang, session.band))
                if self._debug and session.band is not None:
                    yield click.style(session.watched.said(session.band), dim=True)
                seen += 1
                if seen == limit:
                    return
            yield from self._answer(message['seq'])

    def _answer(self, seq: int) -> Iterator[str]:
        session = self._session
        if not session.asked:
            return
        if session.council is None:
            session.answer(seq)
            return
        known = session.known()
        if known is not None and session.place is not None:
            yield from pictured(known, session.colours, session.place)
            if self._debug and session.band is not None:
                session.stocked()
                yield click.style(session.watched.said(session.band), dim=True)
        yield coloured([Part(Look.STATUS, render(STATUS, {'status': session.status}, self._lang))])
        session.answer(seq, self._choose(options(session.council, session.place), self._lang, session.place))
