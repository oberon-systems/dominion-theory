"""
Playing a game as lines, for an input that is not a terminal: a coloured line per update, and every morning
the map and a numbered list of the council's answers, with the places of a go one level below.
"""

from collections.abc import Callable, Iterator, Mapping
from typing import Any

import click

from ..i18n import render
from .api import Api
from .drawing import pictured
from .lines import (
    ANSWER,
    GO,
    KIND,
    KINDS,
    POINT,
    QUESTION,
    SILENCE,
    STATUS,
    UNCLEAR,
    WHERE,
    Look,
    Menu,
    Option,
    Part,
    menu,
    parts,
    where,
)
from .session import Session

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
NAMES = {
    'go': GO,
    'roam': GO,
    **{kind: kind for kind in KINDS},
    'stay': 'stay-and-gather',
    'winter': 'winter-camp',
    'w': 'winter-camp',
}
LEADING: dict[str, Any] = {'fg': 'green', 'bold': True}
# A place answered with nothing: back to the answers.
RETURN: Mapping[str, Any] = {'kind': 'back'}

type Proposal = Mapping[str, Any]
type Place = tuple[int, int]
type Choose = Callable[[Menu, str], Proposal]


def coloured(said: list[Part]) -> str:
    return ''.join(click.style(part.text, **STYLES[part.look]) for part in said)


def label(option: Option, lang: str) -> str:
    return render(f'{KIND}{option.kind}', lang=lang) if option.way is None else where(option.way, lang)


def marked(option: Option, lang: str) -> str:
    """
    The label in the colour of the leader when most of the band leans to it.
    """
    return click.style(label(option, lang), **LEADING) if option.leader else label(option, lang)


def understood(answer: str, listed: list[Option]) -> Option | None:
    """
    A number of the answers or a name; nothing says nothing.
    """
    said = answer.strip().lower()
    if said.isdigit():
        number = int(said)
        return listed[number - 1] if 1 <= number <= len(listed) else None
    kind = NAMES.get(said) if said else SILENCE['kind']
    return next((option for option in listed if option.kind == kind), None)


def pointed(answer: str, places: list[Option], place: Place | None = None) -> Proposal | None:
    """
    A number of the places, a point as two offsets from the band, x then y ('+3 -2'), or nothing to go back.
    """
    said = answer.strip()
    if not said:
        return RETURN
    if said.isdigit():
        number = int(said)
        return places[number - 1].proposal if 1 <= number <= len(places) else None
    offsets = said.split()
    if place is not None and len(offsets) == 2 and all(_offset(word) for word in offsets):
        dx, dy = (int(word) for word in offsets)
        return {'kind': GO, 'to': {'x': place[0] + dx, 'y': place[1] + dy}}
    return None


def _offset(word: str) -> bool:
    return word.lstrip('+-').isdigit() and word.count('+') + word.count('-') <= 1


def _asked[T](question: str, said: list[str], hint: str, read: Callable[[str], T | None], lang: str) -> T:
    click.echo(render(question, lang=lang))
    for number, text in enumerate(said, 1):
        click.echo(f'{number}. {text}')
    while True:
        answer = click.prompt(render(hint, lang=lang), default='', show_default=False)
        chosen = read(answer)
        if chosen is not None:
            return chosen
        click.echo(render(UNCLEAR, {'answer': answer}, lang))


def prompted(given: Menu, lang: str) -> Proposal:
    """
    The answers as numbered lines; a go asks for its place the same way, and coming back asks again.
    """
    while True:
        said = [marked(option, lang) for option in given.answers]
        chosen = _asked(QUESTION, said, ANSWER, lambda answer: understood(answer, given.answers), lang)
        if chosen.proposal is not None:
            return chosen.proposal
        places = [marked(option, lang) for option in given.places]
        proposal = _asked(WHERE, places, POINT, lambda answer: pointed(answer, given.places, given.place), lang)
        if proposal is not RETURN:
            return proposal


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
        session.answer(seq, self._choose(menu(session.council, session.place, session.watched.known.get), self._lang))
