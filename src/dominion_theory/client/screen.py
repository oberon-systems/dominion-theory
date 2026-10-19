"""
Playing a game in a terminal as a screen of two panes: on the left the land the band knows, the band, its
place and the council's menu, with the skills, the stores or the people of the band opened by a key; on the
right the log of what happened.
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
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import OptionList, RichLog, Static
from textual.widgets.option_list import Option as Choice
from websockets.exceptions import WebSocketException

from ..i18n import DATE, render
from .api import ENDED, Body, Refused
from .drawing import HIDDEN, pictured
from .lines import (
    AGREED,
    CAMP,
    CURSOR,
    EVENING,
    FATIGUE,
    GONE,
    INTENT,
    KEYS,
    NEXT,
    NO_SKILLS,
    NO_STORES,
    OVER,
    PEOPLE,
    PICK,
    PROPERTY,
    QUESTION,
    RIVER,
    SILENCE,
    SKILL,
    STATE,
    STATUS,
    TITLE,
    UNKNOWN,
    WHERE,
    Look,
    Menu,
    Option,
    Part,
    doing,
    held_parts,
    intended,
    menu,
    parts,
    people_parts,
    sheltered,
    target,
    words,
)
from .player import coloured, label
from .session import Session

PACE_S = 0.0
BAR = 10
SEEN = 'seen'
ACCEPTED = 'command-accepted'
LOOKS = {Look.BAND: 'cyan', Look.STATE: 'bold red'}
LEADING = 'bold green'
FAILURES = (httpx.HTTPError, WebSocketException, OSError)
ANSWERS = 'answers'
PLACES = 'places'
POINTING = 'pointing'
RESTING = 'resting'
STEPS = {
    'up': (0, -1),
    'k': (0, -1),
    'down': (0, 1),
    'j': (0, 1),
    'left': (-1, 0),
    'h': (-1, 0),
    'right': (1, 0),
    'l': (1, 0),
}
POINTED = ('step', 'pick')
RESEARCH = 'research'
STORES = 'stores'
KIN = 'people'
# The panes a key opens under the band, and closes again.
DETAILS = {'r': RESEARCH, 's': STORES, 'i': KIN}
LEARNED = '✓ '
UNLEARNED = '· '


def details(band: Mapping[str, Any], skills: list[str], pane: str, lang: str) -> Text:
    """
    A pane opened by its key: every skill of the game, those learned first marked; the stores and the goods;
    the people by stage, condition and role.
    """
    if pane == RESEARCH:
        known = band.get('lore', [])
        lines = [] if known else [Part(Look.PLAIN, render(NO_SKILLS, lang=lang))]
        for name in skills or known:
            mark, look = (LEARNED, Look.BAND) if name in known else (UNLEARNED, Look.PLAIN)
            lines.append(Part(look, mark + render(f'{SKILL}{name}', lang=lang)))
    elif pane == STORES:
        lines = held_parts(band, lang) or [Part(Look.PLAIN, render(NO_STORES, lang=lang))]
    else:
        lines = [Part(Look.BAND, render(PEOPLE, {'count': band['population']}, lang))]
        lines += people_parts(band, lang, every=True)
    told = Text()
    for at, part in enumerate(lines):
        told.append(('\n' if at else '') + part.text, LOOKS.get(part.look, 'dim'))
    return told


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
    #date { height: 1; }
    #land { height: 1fr; }
    #map { width: auto; min-width: 20; border: round $primary; }
    #panels { width: 1fr; height: 1fr; }
    #band, #cell { border: round $primary; padding: 0 1; height: auto; }
    #detail { border: round $secondary; padding: 0 1; height: auto; }
    #council { border: round $accent; padding: 0 1; height: auto; }
    #menu { height: auto; max-height: 13; border: none; }
    """
    BINDINGS = [
        Binding('q', 'leave', show=False),
        Binding('ctrl+c', 'leave', show=False, priority=True),
        *(Binding(key, f'step({dx}, {dy})', show=False, priority=True) for key, (dx, dy) in STEPS.items()),
        Binding('enter', 'pick', show=False, priority=True),
        Binding('escape', 'retreat', show=False, priority=True),
        *(Binding(key, f"detail('{pane}')", show=False) for key, pane in DETAILS.items()),
    ]

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
        self._chosen: queue.Queue[Mapping[str, Any] | None] = queue.Queue()
        self._menu: Menu | None = None
        self._mode: str | None = None
        self._lit: tuple[int, int] | None = None
        self._cursor: tuple[int, int] | None = None
        self._known: Body | None = None
        self._drawn_at: tuple[int, int] | None = None
        self._detail: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='control'):
                yield Static(id='date')
                with Horizontal(id='land'):
                    yield Static(id='map')
                    with VerticalScroll(id='panels'):
                        yield Static(id='band')
                        yield Static(id='detail')
                        yield Static(id='cell')
                with Vertical(id='council'):
                    yield Static(id='question')
                    yield OptionList(id='menu')
            yield RichLog(id='log', wrap=True, markup=False)

    def on_mount(self) -> None:
        for pane in ('band', 'cell', 'log', 'council'):
            self.query_one(f'#{pane}').border_title = render(f'{TITLE}{pane}', lang=self._lang)
        self.query_one('#band').border_subtitle = render(KEYS, lang=self._lang)
        self.query_one('#council').display = False
        self.query_one('#detail').display = False
        self._draw()
        threading.Thread(target=self._play, daemon=True).start()

    def action_leave(self) -> None:
        self._chosen.put(None)
        self.exit()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if self._mode != PLACES or self._menu is None:
            return
        places = self._menu.places
        proposal = places[event.option_index].proposal if event.option_index < len(places) else None
        self._lit = None if proposal is None else target(proposal)
        self._draw()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        index, given = event.option_index, self._menu
        if given is None or self._mode not in (ANSWERS, PLACES):
            self._send(SILENCE)
        elif self._mode == ANSWERS and given.answers[index].proposal is None:
            self._places()
        elif self._mode == ANSWERS:
            self._send(given.answers[index].proposal)
        elif index < len(given.places):
            self._send(given.places[index].proposal)
        elif given.pointing:
            self._point()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # The keys of the cursor are the menu's while no cell is being picked; Esc steps back from both.
        if action == 'retreat':
            return self._mode in (PLACES, POINTING)
        return self._mode == POINTING if action in POINTED else True

    def action_step(self, dx: int, dy: int) -> None:
        known = self._known
        if self._cursor is None or known is None:
            return
        x = min(max(self._cursor[0] + dx, known['x']), known['x'] + known['width'] - 1)
        y = min(max(self._cursor[1] + dy, known['y']), known['y'] + known['height'] - 1)
        self._cursor = (x, y)
        self._draw()

    def action_pick(self) -> None:
        if self._cursor is not None and self._cursor != self._session.place:
            self._send({'kind': 'go', 'to': {'x': self._cursor[0], 'y': self._cursor[1]}})

    def action_detail(self, pane: str) -> None:
        self._detail = None if self._detail == pane else pane
        self._draw()

    def action_retreat(self) -> None:
        if self._mode == POINTING:
            self._places()
        else:
            self._answers()

    def _send(self, proposal: Mapping[str, Any] | None) -> None:
        self._mode, self._lit, self._cursor = None, None, None
        self.query_one('#council').display = False
        self._draw()
        self._chosen.put(SILENCE if proposal is None else proposal)

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
        self.call_from_thread(self._ask, menu(session.council, session.place, session.watched.known.get), known)
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
        self._mode = RESTING
        self._listing(Text(render(EVENING, lang=self._lang)), [Text(render(NEXT, lang=self._lang))], 0)

    def _shown(self, message: Mapping[str, Any], known: Body | None) -> None:
        told = {**message, 'events': [event for event in message['events'] if event['key'] != ACCEPTED]}
        said = parts(told, self._lang)
        if len(said) > 1:
            self.query_one('#log', RichLog).write(Text.from_ansi(coloured(said)))
        if known is not None:
            self._known = known
        self._draw()

    def _ask(self, given: Menu, known: Body | None) -> None:
        self._menu = given
        if known is not None:
            self._known = known
        self._answers()

    def _answers(self) -> None:
        if self._menu is None:
            return
        self._mode, self._lit, self._cursor = ANSWERS, None, None
        question = Text(render(QUESTION, lang=self._lang) + ' ')
        question.append(render(STATUS, {'status': self._session.status}, self._lang), 'bold yellow')
        answers = self._menu.answers
        leader = next((index for index, option in enumerate(answers) if option.leader), 0)
        self._listing(question, [self._label(option) for option in answers], leader)

    def _places(self) -> None:
        if self._menu is None:
            return
        places = self._menu.places
        self._mode, self._cursor = PLACES, None
        self._lit = None if not places or places[0].proposal is None else target(places[0].proposal)
        said = [self._label(option) for option in places]
        if self._menu.pointing:
            said.append(Text(render(PICK, lang=self._lang)))
        self._listing(Text(render(WHERE, lang=self._lang)), said, 0)

    def _label(self, option: Option) -> Text:
        return Text(label(option, self._lang), LEADING if option.leader else '')

    def _point(self) -> None:
        self._mode, self._cursor = POINTING, self._session.place
        self.query_one('#question', Static).update(render(CURSOR, lang=self._lang))
        self.query_one('#menu').display = False
        self.set_focus(None)
        self._draw()

    def _listing(self, question: Text, said: list[Text], highlighted: int) -> None:
        self.query_one('#question', Static).update(question)
        listed = self.query_one('#menu', OptionList)
        listed.display = True
        listed.clear_options()
        listed.add_options([Choice(text) for text in said])
        listed.highlighted = highlighted
        self.query_one('#council').display = True
        listed.focus()
        self._draw()

    def _over(self) -> None:
        self.query_one('#question', Static).update(render(ended(self._session), lang=self._lang))
        self.query_one('#menu').display = False
        self.query_one('#council').display = True

    def _draw(self) -> None:
        session = self._session
        if session.date is not None:
            self.query_one('#date', Static).update(Text(render(DATE, session.date, self._lang), 'bold'))
        if self._known is not None and session.place is not None:
            drawn = '\n'.join(pictured(self._known, session.colours, session.place, self._lit, self._cursor))
            self.query_one('#map', Static).update(Text.from_ansi(drawn))
        self.query_one('#band', Static).update(self._band())
        detail = self.query_one('#detail', Static)
        detail.display = self._detail is not None
        if self._detail is not None:
            detail.border_title = render(f'{TITLE}{self._detail}', lang=self._lang)
            detail.update(self._details(self._detail))
        self.query_one('#cell', Static).update(self._cell())

    def _band(self) -> Text:
        session = self._session
        band = session.band
        told = Text()
        if band is None:
            told.append(render(GONE, lang=self._lang) + '\n', 'bold red')
        else:
            told.append(render(PEOPLE, {'count': band['population']}, self._lang) + '\n', LOOKS[Look.BAND])
            if sheltered(band):
                told.append(render(CAMP, lang=self._lang) + '\n', LOOKS[Look.BAND])
            for state in band['states']:
                told.append(render(f'{STATE}{state}', lang=self._lang) + '\n', LOOKS[Look.STATE])
            told.append(doing(band['action'], self._lang) + '\n', LOOKS[Look.BAND])
            told.append(render(FATIGUE, {'fatigue': band['fatigue']}, self._lang) + '\n')
            if band.get('intent'):
                said = intended(band['intent']['proposal'], session.place, session.watched.known.get, self._lang)
                told.append(render(INTENT, {'proposal': said}, self._lang) + '\n', 'magenta')
        told.append(render(STATUS, {'status': session.status}, self._lang), 'bold yellow')
        return told

    def _details(self, pane: str) -> Text:
        band = self._session.band
        return Text() if band is None else details(band, self._session.skills, pane, self._lang)

    def _cell(self) -> Text:
        session = self._session
        told = Text()
        looked = self._cursor or self._lit or session.place
        pane = 'cell' if looked == session.place else 'target'
        self.query_one('#cell').border_title = render(f'{TITLE}{pane}', lang=self._lang)
        if looked is None:
            return told
        seen = session.watched.cell(looked)
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
