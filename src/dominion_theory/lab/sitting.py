"""
One game played from the seat over the API, as text: what the seat sees, the council numbered, the answer by its
number, the story between two looks; the tools of the MCP server `dominion` speak through it, docs/lab/players.md.
"""

from collections.abc import Callable, Mapping
from contextlib import closing
from typing import Any

import click

from ..client import Api, Session
from ..client.drawing import glyph, pictured
from ..client.lines import (
    ABSTAIN,
    FATIGUE,
    GO,
    GONE,
    INTENT,
    KIND,
    NO_SKILLS,
    NO_STORES,
    PEOPLE,
    PROPERTY,
    RIVER,
    SILENCE,
    SKILL,
    STATUS,
    TITLE,
    band_words,
    held_parts,
    intended,
    parts,
    people_parts,
    target,
    way,
    where,
)
from ..i18n import DATE, FALLBACK, check_language, render

STEP = 'step'
# Every tick of step mode carries them; the story leaves them out.
QUIET = frozenset({'day-started', 'command-accepted'})
DAY = 'day-started'
OCCASION = 'occasion-'
BIOME = 'biome-'
ROUNDED = 2
SEAT = 'seat-'
GAME = f'{SEAT}game'
NO_GAME = f'{SEAT}no-game'
OVER = f'{SEAT}over'
ENDED = f'{SEAT}ended'
BAND = f'{SEAT}band'
LAND = f'{SEAT}land'
LEGEND = f'{SEAT}legend'
SITS = f'{SEAT}sits'
NO_COUNCIL = f'{SEAT}no-council'
COUNCIL = f'{SEAT}council'
OPTION = f'{SEAT}option'
LEADS = f'{SEAT}option-leads'
SILENT = f'{SEAT}silence'
NO_OPTION = f'{SEAT}no-option'
STORY = f'{SEAT}story'
QUIET_STORY = f'{SEAT}quiet'
MESSAGES: tuple[str, ...] = (
    GAME,
    NO_GAME,
    OVER,
    *(f'{OVER}-{end}' for end in ('banished', 'died')),
    ENDED,
    BAND,
    LAND,
    LEGEND,
    SITS,
    NO_COUNCIL,
    COUNCIL,
    OPTION,
    LEADS,
    SILENT,
    NO_OPTION,
    STORY,
    QUIET_STORY,
)
PROPERTIES = ('food', 'water', 'threat', 'passability')
LEARNED = '+ '
UNLEARNED = '- '
# A council that never sits for the seat still leaves the turn to the player within a year.
MOST_DAYS = 100

type Stop = Callable[[Mapping[str, Any]], bool]


def _number(value: float) -> str:
    return f'{round(value, ROUNDED):g}'


class Sitting:
    """
    The seat of one game at a time, in step mode: every tick the seat is not asked at a council is passed.
    """

    def __init__(self, api: Api, overrides: Mapping[str, Any] | None = None) -> None:
        self.api = api
        self.overrides = dict(overrides or {})
        self.lang = FALLBACK
        self.session: Session | None = None
        self.over = False
        self._story: list[str] = []

    def new_game(self, seed: int | None = None, preset: str | None = None, lang: str = FALLBACK) -> str:
        """
        A new game with the seat taken, in place of the one played; what the seat sees at its start.
        """
        self.lang = check_language(lang)
        if self.session is not None and not self.over:
            self.api.end(self.session.game)
        game = self.api.create(STEP, seed, preset, self.overrides, seated=True)
        self.session, self.over, self._story = Session(self.api, game['id']), False, []
        return '\n'.join([self._say(GAME, game=game['id'], seed=str(game['seed'])), self.look()])

    def look(self) -> str:
        """
        The date and the standing, the band, the land it knows around it, whether a council sits, and the story
        since the last look.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        said = [f'{render(DATE, session.date, self.lang)}. {self._say(STATUS, status=session.status)}']
        band = session.band
        if band is None:
            said.append(self._say(GONE))
        else:
            said.append(self._say(BAND, band=band_words(band, self.lang)))
            held = [self._say(FATIGUE, fatigue=band['fatigue'])]
            if band.get('intent'):
                proposal = intended(band['intent']['proposal'], session.place, session.watched.known.get, self.lang)
                held.append(self._say(INTENT, proposal=proposal))
            said.append('; '.join(held) + '.')
            said += self._land()
        if self.over:
            said.append(self._ended())
        elif session.council is not None:
            said.append(self._say(SITS))
        said += self._told()
        return '\n'.join(said)

    def council(self) -> str:
        """
        The table of the council that sits, numbered: every option the others voted for in its order, abstaining
        after them, 0 for silence.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        if session.council is None or self.over:
            return self._say(NO_COUNCIL)
        sitting = session.council
        session.known()
        said = [self._say(COUNCIL, occasion=f'{OCCASION}{sitting.get("occasion")}', voice=sitting.get('voice') or 0)]
        for number, entry in enumerate(sitting['table'], 1):
            values = {'number': number, 'option': self._option(entry['proposal']), 'votes': entry['votes']}
            leads = entry['proposal'] == sitting.get('leader')
            said.append(self._say(LEADS if leads else OPTION, **values, score=entry.get('score') or 0.0))
            ground = self._ground(entry['proposal'])
            if ground:
                said[-1] += f' {ground}'
        said.append(f'{len(sitting["table"]) + 1}. {self._say(f"{KIND}{ABSTAIN}")}')
        said.append(self._say(SILENT))
        return '\n'.join(said)

    def vote(self, number: int) -> str:
        """
        The answer by its number of the table; the tick it closes is played and its story told.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        if session.council is None or not session.asked or self.over:
            return self._say(NO_COUNCIL)
        table = session.council['table']
        if not 0 <= number <= len(table) + 1:
            return self._say(NO_OPTION, number=number, last=len(table) + 1)
        if number == 0:
            session.answer(session.seq)
        else:
            session.answer(session.seq, table[number - 1]['proposal'] if number <= len(table) else SILENCE)
        self._read(lambda _: True)
        return '\n'.join(self._told())

    def advance(self, days: int | None = None) -> str:
        """
        Passes until a council sits for the seat, or until the days given have begun, at most MOST_DAYS; the
        story in between.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        if session.council is not None and session.asked and not self.over:
            return self._say(SITS)
        begun = [0]

        def enough(update: Mapping[str, Any]) -> bool:
            begun[0] += sum(event['key'] == DAY for event in update['events'])
            return begun[0] >= min(days or MOST_DAYS, MOST_DAYS)

        if session.asked and not self.over:
            session.answer(session.seq)
        self._read(enough)
        said = self._told()
        if self.over:
            said.append(self._ended())
        elif session.council is not None:
            said.append(self._say(SITS))
        return '\n'.join(said)

    def panes(self) -> str:
        """
        The people one by one by stage, condition and role; every skill of the game, those learned marked; the
        stores and the goods.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        band = session.band
        if band is None:
            return self._say(GONE)
        people = [self._say(PEOPLE, count=band['population'])]
        people += [part.text for part in people_parts(band, self.lang, every=True)]
        known = band.get('lore', [])
        skills = [(LEARNED if name in known else UNLEARNED) + self._say(f'{SKILL}{name}') for name in session.skills]
        stores = [part.text for part in held_parts(band, self.lang)]
        held = f'{", ".join(stores)}.' if stores else self._say(NO_STORES)
        return '\n'.join(
            [
                f'{self._say(f"{TITLE}people")}: {", ".join(people)}.',
                f'{self._say(f"{TITLE}research")}:',
                *(skills or [self._say(NO_SKILLS)]),
                f'{self._say(f"{TITLE}stores")}: {held}',
            ]
        )

    def end(self) -> str:
        """
        Ends the game played; its record is the one make replay plays.
        """
        session = self.session
        if session is None:
            return self._say(NO_GAME)
        if not self.over:
            self.api.end(session.game)
            self.over = True
        return self._say(ENDED, game=session.game)

    def _say(self, key: str, **values: Any) -> str:
        return render(key, values, self.lang)

    def _read(self, stop: Stop) -> None:
        """
        Reads the updates after the seat's last answer, passing every tick the seat is asked with no council, until
        the seat is asked at a council or stop holds; the end of the stream ends the game.
        """
        session = self.session
        if session is None or self.over:
            return
        with closing(session.stream()) as messages:
            for message in messages:
                if message.get('resync'):
                    continue
                self._story += self._line(message)
                if not session.asked:
                    continue
                if session.council is not None or stop(message):
                    return
                session.answer(message['seq'])
        self.over = True

    def _line(self, update: Mapping[str, Any]) -> list[str]:
        told = {**update, 'events': [event for event in update['events'] if event['key'] not in QUIET]}
        said = parts(told, self.lang)
        return [''.join(part.text for part in said)] if len(said) > 1 else []

    def _told(self) -> list[str]:
        said = [self._say(STORY), *self._story] if self._story else [self._say(QUIET_STORY)]
        self._story = []
        return said

    def _land(self) -> list[str]:
        session = self.session
        if session is None or session.place is None:
            return []
        known = session.known()
        if known is None:
            return []
        rows = [click.unstyle(row) for row in pictured(known, {}, session.place, camps=session.camps)]
        seen = sorted({known['biomes'][cell] for cell in known['cells'] if cell is not None})
        signs = ', '.join(f'{glyph(biome)} {self._say(f"{BIOME}{biome}")}' for biome in seen)
        return [self._say(LAND), *rows, self._say(LEGEND, signs=signs)]

    def _option(self, proposal: Mapping[str, Any]) -> str:
        session = self.session
        if proposal['kind'] == GO and session is not None and session.place is not None:
            return where(way(target(proposal), session.place, session.watched.known.get), self.lang)
        return self._say(f'{KIND}{proposal["kind"]}')

    def _ground(self, proposal: Mapping[str, Any]) -> str:
        """
        The land an option keeps the band on, as it knows it: the biome, its food, water, threat and passability,
        a river.
        """
        session = self.session
        if session is None or session.place is None:
            return ''
        cell = session.watched.known.get(target(proposal) if proposal['kind'] == GO else session.place)
        if cell is None:
            return ''
        held = [self._say(f'{BIOME}{cell["biome"]}')]
        held += [f'{self._say(f"{PROPERTY}{name}")} {_number(cell[name])}' for name in PROPERTIES if name in cell]
        if cell.get('river'):
            held.append(self._say(RIVER))
        return f'({", ".join(held)})'

    def _ended(self) -> str:
        session = self.session
        if session is not None and session.status <= 0:
            return self._say(f'{OVER}-banished')
        if session is not None and session.band is None:
            return self._say(f'{OVER}-died')
        return self._say(OVER)
