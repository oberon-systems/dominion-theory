"""
Played games read back from their records: a list of them with a summary each, and a game played again on a
screen of the planet, the window with the trail of the band, the band and its panes, the log and charts.
"""

import bisect
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, RichLog, Static
from textual_plotext import PlotextPlot

from ..i18n import DATE, render
from ..runner.replays import UNREADABLE, Frame, Played, Summary, played, summaries
from .drawing import BAND, RIVER, glyph, rgb
from .lines import STATE, doing, parts
from .player import coloured
from .screen import KIN, RESEARCH, STORES, details

REVIEW = 'review-'
TITLE = f'{REVIEW}title-'
COLUMN = f'{REVIEW}column-'
OUTCOME = f'{REVIEW}outcome-'
CHART = f'{REVIEW}chart-'
COLUMNS = ('game', 'written', 'seed', 'seat', 'length', 'outcome', 'people', 'born', 'died', 'skills', 'status')
# Ticks a second the game is played at, the third the first.
PACES = (1, 2, 5, 10, 25, 50, 100, 250, 500)
FIRST_PACE = 3
FRAME_S = 0.05
LOG_KEPT = 300
TRAIL = '·'
CAMP = '^'
FRAME = (255, 255, 255)
MARK = (255, 0, 255)
# The most of the left column the planet may take.
PLANET_SHARE = 0.5
SKIPPED = ('command-accepted',)
PLOT_S = 0.2
NEVER = 1 << 62
# The charts Tab steps through: counters drawn in each.
CHARTS = {
    'people': ('population', 'child', 'adult', 'elder'),
    'stores': ('food', 'water'),
    'standing': ('status', 'skills', 'hunters'),
    'losses': ('deaths', 'encounters', 'injured', 'sick', 'pregnant'),
}
PANES = {'i': KIN, 'r': RESEARCH, 's': STORES}
OUTCOMES = ('died', 'banished', 'stopped', 'unfinished', 'unreadable')
TITLES = ('games', 'planet', 'window', 'band', 'log', 'charts')
FARING = ('sick', 'hungry', 'thirsty')
STAGE = f'{REVIEW}stage-'
ROLE = f'{REVIEW}role-'
WOUND = f'{REVIEW}wound-'
MASTERY = f'{REVIEW}mastery'
MEAT = f'{REVIEW}meat'
MESSAGES: tuple[str, ...] = (
    *(f'{TITLE}{name}' for name in TITLES),
    *(f'{COLUMN}{name}' for name in COLUMNS),
    *(f'{OUTCOME}{name}' for name in OUTCOMES),
    *(f'{CHART}{name}' for name in CHARTS),
    *(f'{REVIEW}{name}' for name in FARING),
    *(
        f'{REVIEW}{name}'
        for name in (
            'seated',
            'headless',
            'length',
            'people',
            'pace',
            'paused',
            'keys',
            'list-keys',
            'none',
            'old',
            'guessed',
            'years',
            'pregnant',
            'you',
            'members-none',
            'mastery',
            'meat',
        )
    ),
)

type Rgb = tuple[int, int, int]


def _ink(paper: Rgb) -> Rgb:
    red, green, blue = paper
    return (0, 0, 0) if 0.299 * red + 0.587 * green + 0.114 * blue > 128 else (255, 255, 255)


def _style(paper: Rgb, bold: bool = False) -> Style:
    return Style(color=f'rgb{_ink(paper)}', bgcolor=f'rgb{paper}', bold=bold)


def row(summary: Summary, lang: str) -> list[str]:
    """
    A game as a row of the list, in the order of COLUMNS.
    """
    when = time.strftime('%Y-%m-%d %H:%M', time.localtime(summary.written))
    if summary.outcome == UNREADABLE:
        return [summary.game, when, *([''] * 3), render(f'{OUTCOME}{UNREADABLE}', lang=lang), *([''] * 5)]
    years, days = divmod(summary.days, summary.days_a_year)
    seat = render(f'{REVIEW}seated' if summary.seated else f'{REVIEW}headless', lang=lang)
    people = render(f'{REVIEW}people', {'start': summary.start, 'end': summary.end, 'most': summary.most}, lang)
    return [
        summary.game,
        when,
        str(summary.seed),
        seat,
        render(f'{REVIEW}length', {'years': years, 'days': days}, lang),
        render(f'{OUTCOME}{summary.outcome}', lang=lang),
        people,
        str(summary.born),
        str(summary.died),
        str(summary.skills),
        '' if summary.status is None else f'{summary.status:.1f}',
    ]


def member(held: Mapping[str, Any], days_a_year: int, lang: str) -> str:
    """
    One member in a line: sex, age, stage, role, how it fares, what it holds and makes, and the meat it eats.
    """
    sex = '♀' if held['sex'] == 'female' else '♂'
    said = [
        f'{sex} ' + render(f'{REVIEW}years', {'years': held['age_days'] / days_a_year}, lang),
        render(f'{STAGE}{held["stage"]}', lang=lang),
        render(f'{ROLE}{held["role"]}', lang=lang),
    ]
    if held['player']:
        said.append(render(f'{REVIEW}you', lang=lang))
    if held['pregnant']:
        said.append(render(f'{REVIEW}pregnant', lang=lang))
    if held['wound'] is not None:
        said.append(render(f'{WOUND}{held["wound"]}', lang=lang))
    for state in FARING:
        if held[state]:
            said.append(render(f'{REVIEW}{state}', lang=lang))
    said += [render('line-gathered', {'resource': name}, lang) for name in held['kit']]
    said += [
        render(MASTERY, {'resource': name, 'mastery': level}, lang) for name, level in held.get('craft', {}).items()
    ]
    if held.get('meat'):
        said.append(render(MEAT, {'share': held['meat']}, lang))
    return ', '.join(said)


class Games(Screen[None]):
    """
    The played games, the latest first; Enter plays the one under the cursor.
    """

    BINDINGS = [Binding('q', 'app.quit', show=False)]

    def __init__(self, directory: Path, lang: str) -> None:
        super().__init__()
        self._directory = directory
        self._lang = lang
        self._found: list[Summary] = []

    def compose(self) -> ComposeResult:
        with Vertical(id='games'):
            yield DataTable(id='table', cursor_type='row', zebra_stripes=True)
            yield Static(id='hint')

    def on_mount(self) -> None:
        self.query_one('#games').border_title = render(f'{TITLE}games', lang=self._lang)
        table = self.query_one('#table', DataTable)
        table.add_columns(*(render(f'{COLUMN}{name}', lang=self._lang) for name in COLUMNS))
        self._found = summaries(self._directory)
        for summary in self._found:
            table.add_row(*row(summary, self._lang), key=summary.game)
        hint = 'list-keys' if self._found else 'none'
        self.query_one('#hint', Static).update(
            render(f'{REVIEW}{hint}', {'directory': str(self._directory)}, self._lang)
        )
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        chosen = next(summary for summary in self._found if summary.game == event.row_key.value)
        if chosen.outcome != UNREADABLE:
            self.app.push_screen(Playback(played(chosen.path), self._lang, back=True))


class Playback(Screen[None]):
    """
    One game played again from its frames: a timer moves the frame at the pace, the keys move it by hand.
    """

    BINDINGS = [
        Binding('q', 'back', show=False, priority=True),
        Binding('space', 'pause', show=False, priority=True),
        Binding('plus,equals_sign', 'pace(1)', show=False, priority=True),
        Binding('minus', 'pace(-1)', show=False, priority=True),
        Binding('right', 'move(1)', show=False, priority=True),
        Binding('left', 'move(-1)', show=False, priority=True),
        Binding('up,shift+right', 'days(1)', show=False, priority=True),
        Binding('down,shift+left', 'days(-1)', show=False, priority=True),
        Binding('pageup,right_square_bracket', 'months(1)', show=False, priority=True),
        Binding('pagedown,left_square_bracket', 'months(-1)', show=False, priority=True),
        Binding('home', 'jump(0)', show=False, priority=True),
        Binding('end', 'jump(-1)', show=False, priority=True),
        Binding('tab', 'chart', show=False, priority=True),
        *(Binding(key, f"pane('{pane}')", show=False, priority=True) for key, pane in PANES.items()),
    ]

    def __init__(self, game: Played, lang: str, back: bool = False) -> None:
        super().__init__()
        self._game = game
        self._lang = lang
        self._back = back
        self._at = 0
        self._pace = FIRST_PACE
        self._paused = False
        self._owed = 0.0
        self._pane: str | None = None
        self._chart = 0
        self._logged = -1
        time_ = game.params.time
        self._per_day = time_.parts_per_day
        self._days_a_year = time_.days_per_year
        self._days = [frame.parts // self._per_day for frame in game.frames]
        self._months = [frame.parts // (self._per_day * time_.days_per_month) for frame in game.frames]
        self._walked, self._camps = _trail(game.frames)
        self._colours = [rgb(game.params.biomes[name].colour) for name in game.lands.names]
        self._planet_at: tuple[Any, ...] | None = None
        self._planet_drawn = Text()
        self._planet_grid: tuple[int, list[list[int]]] | None = None
        self._plotted = (-1, -1, 0.0)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id='left'):
                yield Static(id='date')
                yield Static(id='planet')
                yield Static(id='window')
            with Vertical(id='right'):
                with VerticalScroll(id='panels'):
                    yield Static(id='band')
                    yield Static(id='detail')
                yield RichLog(id='log', wrap=True, markup=False)
                yield PlotextPlot(id='chart')
        yield Static(id='keys')

    def on_mount(self) -> None:
        for pane in ('planet', 'window', 'band', 'log', 'chart'):
            name = 'charts' if pane == 'chart' else pane
            self.query_one(f'#{pane}').border_title = render(f'{TITLE}{name}', lang=self._lang)
        self.query_one('#detail').display = False
        self.query_one('#keys', Static).update(render(f'{REVIEW}keys', lang=self._lang))
        self.set_interval(FRAME_S, self._tick)
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def action_back(self) -> None:
        if self._back:
            self.app.pop_screen()
        else:
            self.app.exit()

    def action_pause(self) -> None:
        self._paused = not self._paused
        self._draw()

    def action_pace(self, step: int) -> None:
        self._pace = min(max(self._pace + step, 0), len(PACES) - 1)
        self._draw()

    def action_move(self, step: int) -> None:
        self._go(self._at + step)

    def action_days(self, step: int) -> None:
        self._go(_by(self._days, self._at, step))

    def action_months(self, step: int) -> None:
        self._go(_by(self._months, self._at, step))

    def action_jump(self, at: int) -> None:
        self._go(at % len(self._game.frames))

    def action_chart(self) -> None:
        self._chart = (self._chart + 1) % len(CHARTS)
        self._plot(now=True)

    def action_pane(self, pane: str) -> None:
        self._pane = None if self._pane == pane else pane
        self._paused = self._paused or self._pane is not None
        self._draw()

    def _tick(self) -> None:
        if self._paused or self._at >= len(self._game.frames) - 1:
            return
        self._owed += PACES[self._pace] * FRAME_S
        steps = int(self._owed)
        if steps:
            self._owed -= steps
            self._go(self._at + steps)

    def _go(self, at: int) -> None:
        last = len(self._game.frames) - 1
        self._at = min(max(at, 0), last)
        self._draw()

    def _draw(self) -> None:
        frame = self._game.frames[self._at]
        self.query_one('#date', Static).update(self._dated(frame))
        self.query_one('#planet', Static).update(self._planet(frame))
        self.query_one('#window', Static).update(self._window(frame))
        self.query_one('#band', Static).update(self._band(frame))
        detail = self.query_one('#detail', Static)
        detail.display = self._pane is not None
        if self._pane is not None:
            detail.border_title = render(f'play-title-{self._pane}', lang=self._lang)
            detail.update(self._detail(frame, self._pane))
        self._log()
        self._plot(now=self._paused or self._at == len(self._game.frames) - 1)

    def _dated(self, frame: Frame) -> Text:
        part = render(f'time-part-{frame.date["part"]}', lang=self._lang)
        told = Text(f'{part}, ' + render(DATE, frame.date, self._lang), 'bold')
        pace = 'paused' if self._paused else 'pace'
        told.append('  ' + render(f'{REVIEW}{pace}', {'speed': PACES[self._pace]}, self._lang), 'yellow')
        if not self._game.exact:
            told.append('\n' + render(f'{REVIEW}guessed', lang=self._lang), 'dim')
        return told

    def _planet(self, frame: Frame) -> Text:
        """
        The planet two rows to a line, as wide as its pane and no taller than a share of the column, the window
        framed in white and the band's place marked; drawn again when the band crosses a cell of it or the pane
        is resized.
        """
        lands = self._game.lands
        width = lands.planet.biomes.shape[1]
        pane = self.query_one('#planet')
        inside = pane.size.width - 2 if pane.size.width > 2 else width
        lines = max(min(inside // 4, int(self.query_one('#left').size.height * PLANET_SHARE)), 2)
        columns = min(width, lines * 4)
        rows = columns // 2
        scale = self._game.params.eras['band'].cell_km / lands.planet_km * columns / width
        band = None if frame.row is None else (int(frame.row['x'] * scale), int(frame.row['y'] * scale))
        if (band, columns) == self._planet_at:
            return self._planet_drawn
        window = lands.window
        box = (
            int(window.x * scale),
            int(window.y * scale),
            int((window.x + window.width) * scale),
            int((window.y + window.height) * scale),
        )
        grid = self._grid(columns, rows)
        paper = [
            [self._spot(column, row, box, band, grid[row][column]) for column in range(columns)] for row in range(rows)
        ]
        told = Text(no_wrap=True, overflow='crop')
        for line in range(0, rows - 1, 2):
            if line:
                told.append('\n')
            for column in range(columns):
                told.append('▀', Style(color=f'rgb{paper[line][column]}', bgcolor=f'rgb{paper[line + 1][column]}'))
        self._planet_at, self._planet_drawn = (band, columns), told
        return told

    def _grid(self, columns: int, rows: int) -> list[list[int]]:
        """
        The planet cut to that many cells, each the biome most of its block of the read planet holds.
        """
        if self._planet_grid is not None and self._planet_grid[0] == columns:
            return self._planet_grid[1]
        biomes = self._game.lands.planet.biomes
        height, width = biomes.shape
        grid = [
            [int(np.bincount(biomes[down, across].ravel()).argmax()) for across in _spans(width, columns)]
            for down in _spans(height, rows)
        ]
        self._planet_grid = (columns, grid)
        return grid

    def _spot(self, column: int, row: int, box: tuple[int, int, int, int], band: Any, biome: int) -> Rgb:
        left, top, right, bottom = box
        if (column, row) == band:
            return MARK
        edge = (row in (top, bottom) and left <= column <= right) or (column in (left, right) and top <= row <= bottom)
        return FRAME if edge else self._colours[biome]

    def _window(self, frame: Frame) -> Text:
        """
        The window around the band, a cell a character, open whole; the trail walked so far drawn over it.
        """
        lands = self._game.lands
        widget = self.query_one('#window')
        window = lands.window
        width = min(max(widget.size.width - 2, 10), window.width)
        height = min(max(widget.size.height - 2, 5), window.height)
        here = None if frame.row is None else (frame.row['x'], frame.row['y'])
        centre = here or (window.x + window.width // 2, window.y + window.height // 2)
        x = min(max(centre[0] - width // 2, window.x), window.x + window.width - width)
        y = min(max(centre[1] - height // 2, window.y), window.y + window.height - height)
        told = Text()
        for row in range(y, min(y + height, window.y + window.height)):
            for column in range(x, min(x + width, window.x + window.width)):
                index = lands.biomes[row - window.y, column - window.x]
                paper = self._colours[index]
                at = (column, row)
                if at == here:
                    told.append(BAND, _style(paper, bold=True))
                elif self._camps.get(at, NEVER) <= self._at:
                    told.append(CAMP, _style(paper, bold=True))
                elif self._walked.get(at, NEVER) <= self._at:
                    told.append(TRAIL, _style(paper, bold=True))
                elif lands.rivers[row - window.y, column - window.x]:
                    told.append(RIVER, _style(paper))
                else:
                    told.append(glyph(lands.names[index])[:1], _style(paper))
            told.append('\n')
        return told

    def _band(self, frame: Frame) -> Text:
        told = Text()
        band, counted = frame.band, frame.counters
        if band is None:
            told.append(render('line-people', {'count': int(counted.get('population', 0))}, self._lang) + '\n')
            if frame.row is not None:
                told.append(f'{frame.row["state"]}, {frame.row["action"]}\n', 'cyan')
            told.append(render(f'{REVIEW}old', lang=self._lang), 'dim')
            return told
        told.append(render('line-people', {'count': band['population']}, self._lang) + '\n', 'cyan')
        for state in band['states']:
            told.append(render(f'{STATE}{state}', lang=self._lang) + '\n', 'bold red')
        told.append(doing(band['action'], self._lang) + '\n', 'cyan')
        told.append(render('play-fatigue', {'fatigue': band['fatigue']}, self._lang) + '\n')
        if self._game.summary.seated:
            told.append(render('line-status', {'status': counted.get('status', 0.0)}, self._lang), 'bold yellow')
        told.append('\n' + render('play-keys', lang=self._lang), 'dim')
        return told

    def _detail(self, frame: Frame, pane: str) -> Text:
        if frame.band is None:
            return Text(render(f'{REVIEW}old', lang=self._lang), 'dim')
        told = details(frame.band, list(self._game.params.skills), pane, self._lang)
        if pane != KIN:
            return told
        if frame.members is None:
            return told.append('\n' + render(f'{REVIEW}members-none', lang=self._lang), 'dim')
        for held in frame.members:
            told.append('\n' + member(held, self._days_a_year, self._lang))
        return told

    def _log(self) -> None:
        """
        The lines of what happened up to the frame: written on as the game goes, written anew after a jump back.
        """
        log = self.query_one('#log', RichLog)
        start = self._logged + 1
        if self._at < self._logged or self._at - self._logged > LOG_KEPT:
            log.clear()
            start = max(self._at - LOG_KEPT, 0)
        for frame in self._game.frames[start : self._at + 1]:
            events = [event for event in frame.events if event['key'] not in SKIPPED]
            said = parts({'date': frame.date, 'events': events, 'changes': {}}, self._lang)
            if len(said) > 1:
                log.write(Text.from_ansi(coloured(said)))
        self._logged = self._at

    def _plot(self, now: bool = False) -> None:
        moved = (self._at, self._chart) != self._plotted[:2]
        if not moved or (not now and time.monotonic() - self._plotted[2] < PLOT_S):
            return
        self._plotted = (self._at, self._chart, time.monotonic())
        name, shown = list(CHARTS.items())[self._chart]
        chart = self.query_one('#chart', PlotextPlot)
        chart.border_title = render(f'{CHART}{name}', lang=self._lang)
        plt = chart.plt
        plt.clear_data()
        plt.clear_figure()
        days = sorted(set(self._days))
        last = {day: at for at, day in enumerate(self._days)}
        frames = self._game.frames
        for counter in shown:
            if counter in frames[0].counters:
                plt.plot(days, [frames[last[day]].counters[counter] for day in days], label=counter)
        plt.vline(self._days[self._at], 'white')
        plt.xlabel('day')
        chart.refresh()


def _spans(size: int, parts: int) -> list[slice]:
    """
    A length cut into that many slices as even as they come, none of them empty.
    """
    edges = [part * size // parts for part in range(parts + 1)]
    return [slice(edges[part], max(edges[part + 1], edges[part] + 1)) for part in range(parts)]


def _by(marks: list[int], at: int, step: int) -> int:
    """
    The first frame of the day or month that many away from the one at.
    """
    wanted = marks[at] + step
    return min(bisect.bisect_left(marks, wanted), len(marks) - 1)


def _trail(frames: list[Frame]) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], int]]:
    """
    The frame each cell was first walked on, and first built on.
    """
    walked: dict[tuple[int, int], int] = {}
    camps: dict[tuple[int, int], int] = {}
    for at, frame in enumerate(frames):
        if frame.row is not None:
            cell = (frame.row['x'], frame.row['y'])
            walked.setdefault(cell, at)
            if frame.row['action'] == 'build':
                camps.setdefault(cell, at)
    return walked, camps


class Review(App[None]):
    CSS = """
    #games { border: round $primary; }
    #hint { height: 1; }
    #keys { height: auto; }
    #left { width: 3fr; }
    #right { width: 2fr; }
    #date { height: auto; }
    #planet { height: auto; border: round $primary; }
    #window { height: 1fr; border: round $primary; }
    #panels { height: auto; max-height: 50%; }
    #band { border: round $primary; padding: 0 1; height: auto; }
    #detail { border: round $secondary; padding: 0 1; height: auto; }
    #log { height: 1fr; border: round $secondary; }
    #chart { height: 1fr; border: round $accent; }
    """

    def __init__(self, directory: Path, lang: str, game: str | None = None) -> None:
        super().__init__()
        self._directory = directory
        self._lang = lang
        self._game = game

    def on_mount(self) -> None:
        if self._game is None:
            self.push_screen(Games(self._directory, self._lang))
        else:
            self.push_screen(Playback(played(self._directory / f'{self._game}.jsonl.gz'), self._lang))
