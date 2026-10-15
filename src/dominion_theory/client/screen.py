"""
Playing a game in a terminal as a screen of two panes: on the left the land the band knows, the band, its
place and the council's menu; on the right the log of what happened.
"""

import queue
import threading
import time
from collections.abc import Mapping
from typing import Any

import httpx
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import OptionList, RichLog, Static
from textual.widgets.option_list import Option as Choice
from websockets.exceptions import WebSocketException

from ..i18n import DATE, render
from .api import ENDED, Body, Refused
from .drawing import HIDDEN, pictured
from .lines import (
    ABSTAIN,
    AGREED,
    EVENING,
    FATIGUE,
    GONE,
    INTENT,
    NEXT,
    OVER,
    PROPERTY,
    QUESTION,
    RIVER,
    STATUS,
    TITLE,
    UNKNOWN,
    Look,
    Option,
    band_parts,
    options,
    parts,
    proposal_key,
    words,
)
from .player import SILENCE, coloured, label
from .session import Session

PACE_S = 0.2
BAR = 10
SEEN = 'seen'
ACCEPTED = 'command-accepted'
LOOKS = {Look.BAND: 'cyan', Look.STATE: 'bold red'}
FAILURES = (httpx.HTTPError, WebSocketException, OSError)


class Left(Exception):
    """
    The player left while the council waited.
    """


def ended(session: Session) -> str:
    """
    The words of the end of a game: why it ended, when the session tells.
    """
    if session.status <= 0:
        return f'{OVER}-banished'
    if session.band is None:
        return f'{OVER}-died'
    return OVER


def _bar(value: float) -> str:
    filled = round(min(max(value, 0.0), 1.0) * BAR)
    return '█' * filled + '░' * (BAR - filled)


def _number(value: Any) -> str:
    return f'{round(value, 3):g}' if isinstance(value, float) else str(value)


def _moved(change: float | None) -> str:
    return '' if change is None else f' ({change:+.3g})'


class Screen(App[str | None]):
    """
    The game is stepped by a thread of its own; the screen only draws what the session holds and takes the vote.
    """

    CSS = """
    #control { width: 3fr; }
    #log { width: 2fr; border: round $secondary; }
    #land { height: auto; }
    #map { width: auto; min-width: 20; border: round $primary; }
    #panels { width: 1fr; height: auto; }
    #band, #cell { border: round $primary; padding: 0 1; height: auto; }
    #council { border: round $accent; padding: 0 1; height: auto; }
    #menu { height: auto; max-height: 13; border: none; }
    """
    BINDINGS = [Binding('q', 'leave', show=False), Binding('ctrl+c', 'leave', show=False, priority=True)]

    def __init__(
        self,
        session: Session,
        lang: str,
        debug: bool = False,
        pace: float = PACE_S,
        limit: int | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._lang = lang
        self._debug = debug
        self._pace = pace
        self._limit = limit
        self._chosen: queue.Queue[Mapping[str, str] | None] = queue.Queue()
        self._listed: list[Option] = []
        self._known: Body | None = None
        self._drawn_at: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='control'):
                yield Static(id='date')
                with Horizontal(id='land'):
                    yield Static(id='map')
                    with Vertical(id='panels'):
                        yield Static(id='band')
                        yield Static(id='cell')
                with Vertical(id='council'):
                    yield Static(id='question')
                    yield OptionList(id='menu')
            yield RichLog(id='log', wrap=True, markup=False)

    def on_mount(self) -> None:
        for pane in ('band', 'cell', 'log', 'council'):
            self.query_one(f'#{pane}').border_title = render(f'{TITLE}{pane}', lang=self._lang)
        self.query_one('#council').display = False
        self._draw()
        threading.Thread(target=self._play, daemon=True).start()

    def action_leave(self) -> None:
        self._chosen.put(None)
        self.exit()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        index = event.option_index
        self.query_one('#council').display = False
        self._chosen.put(self._listed[index].proposal if index < len(self._listed) else SILENCE)

    def _play(self) -> None:
        session = self._session
        try:
            self._turn(session.seq)
            seen = 0
            for message in session.stream():
                if not message.get('resync'):
                    known = self._land(message)
                    self.call_from_thread(self._shown, message, known)
                    seen += 1
                    if seen == self._limit:
                        break
                    if any(event['key'] == AGREED for event in message['events']):
                        self._rest()
                self._turn(message['seq'])
            self.call_from_thread(self._over)
        except Left:
            return
        except Refused as refused:
            if refused.key == ENDED:
                self.call_from_thread(self._over)
                return
            self.call_from_thread(self.exit, words({'key': refused.key, 'values': refused.values}, self._lang))
        except FAILURES as failure:
            self.call_from_thread(self.exit, str(failure))

    def _land(self, message: Mapping[str, Any]) -> Body | None:
        """
        The map anew when the band has moved or learnt something, None when the drawn one still holds.
        """
        session = self._session
        if session.place == self._drawn_at and not message.get('changes', {}).get('known'):
            return None
        self._drawn_at = session.place
        return session.known()

    def _turn(self, seq: int) -> None:
        session = self._session
        if not session.asked:
            return
        if session.council is None:
            time.sleep(self._pace)
            session.answer(seq)
            return
        known = session.known()
        if self._debug:
            session.stocked()
        self.call_from_thread(self._ask, options(session.council), known)
        proposal = self._chosen.get()
        if proposal is None:
            raise Left
        session.answer(seq, proposal)

    def _rest(self) -> None:
        """
        An evening with no council: the game waits until the player has read the day and goes on.
        """
        self.call_from_thread(self._evening)
        if self._chosen.get() is None:
            raise Left

    def _evening(self) -> None:
        self._listed = []
        self.query_one('#question', Static).update(render(EVENING, lang=self._lang))
        menu = self.query_one('#menu', OptionList)
        menu.clear_options()
        menu.add_option(Choice(render(NEXT, lang=self._lang)))
        menu.highlighted = 0
        self.query_one('#council').display = True
        menu.focus()

    def _shown(self, message: Mapping[str, Any], known: Body | None) -> None:
        told = {**message, 'events': [event for event in message['events'] if event['key'] != ACCEPTED]}
        said = parts(told, self._lang)
        if len(said) > 1:
            self.query_one('#log', RichLog).write(Text.from_ansi(coloured(said)))
        if known is not None:
            self._known = known
        self._draw()

    def _ask(self, listed: list[Option], known: Body | None) -> None:
        self._listed = listed
        if known is not None:
            self._known = known
        self._draw()
        question = Text(render(QUESTION, lang=self._lang) + ' ')
        question.append(render(STATUS, {'status': self._session.status}, self._lang), 'bold yellow')
        self.query_one('#question', Static).update(question)
        menu = self.query_one('#menu', OptionList)
        menu.clear_options()
        menu.add_options([Choice(label(option, self._lang)) for option in listed])
        menu.add_option(Choice(render(ABSTAIN, lang=self._lang)))
        menu.highlighted = next((index for index, option in enumerate(listed) if option.leader), 0)
        self.query_one('#council').display = True
        menu.focus()

    def _over(self) -> None:
        self.query_one('#question', Static).update(render(ended(self._session), lang=self._lang))
        self.query_one('#menu').display = False
        self.query_one('#council').display = True

    def _draw(self) -> None:
        session = self._session
        if session.date is not None:
            self.query_one('#date', Static).update(Text(render(DATE, session.date, self._lang), 'bold'))
        if self._known is not None and session.place is not None:
            drawn = '\n'.join(pictured(self._known, session.colours, session.place))
            self.query_one('#map', Static).update(Text.from_ansi(drawn))
        self.query_one('#band', Static).update(self._band())
        self.query_one('#cell', Static).update(self._cell())

    def _band(self) -> Text:
        session = self._session
        band = session.band
        told = Text()
        if band is None:
            told.append(render(GONE, lang=self._lang) + '\n', 'bold red')
        else:
            for part in band_parts(band, self._lang):
                if part.look != Look.PLAIN:
                    told.append(part.text + '\n', LOOKS.get(part.look, ''))
            told.append(render(FATIGUE, {'fatigue': band['fatigue']}, self._lang) + '\n')
            if band.get('intent'):
                proposal = proposal_key(band['intent']['proposal'])
                told.append(render(INTENT, {'proposal': proposal}, self._lang) + '\n', 'magenta')
        told.append(render(STATUS, {'status': session.status}, self._lang), 'bold yellow')
        return told

    def _cell(self) -> Text:
        session = self._session
        told = Text()
        if session.place is None:
            return told
        seen = session.watched.cell(session.place)
        if seen.known is None:
            return told.append(render(UNKNOWN, lang=self._lang), 'dim')
        name = session.biomes.get(seen.known['biome'], {}).get('name')
        told.append(seen.known['biome'] if name is None else words(name, self._lang), 'bold')
        if seen.known['river']:
            told.append(', ' + render(RIVER, lang=self._lang), 'blue')
        for prop, value in seen.known.items():
            if prop in HIDDEN or value is None or (prop == SEEN and not self._debug):
                continue
            change = _moved(seen.known_moved.get(prop)) if self._debug else ''
            shown = render(f'{PROPERTY}{prop}', lang=self._lang) if prop != SEEN else prop
            bar = '' if prop == SEEN else _bar(value) + ' '
            told.append(f'\n{shown:<12} {bar}{_number(value)}{change}')
        if self._debug:
            stock = seen.stock or {}
            moved = (f'{name} {_number(value)}{_moved(seen.stock_moved.get(name))}' for name, value in stock.items())
            told.append('\nstock ' + ', '.join(moved), 'dim')
            reason = (session.band or {}).get('reason') or {}
            said = (f'{name} {_number(value)}' for name, value in reason.items() if value is not None)
            told.append('\nreason ' + ', '.join(said), 'dim')
        return told
