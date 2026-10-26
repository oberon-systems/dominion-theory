"""
What a band knows of the land around it, drawn as text: a cell is two characters on the colour of its biome.
The cells seen in updates are kept too, so a debug line can tell the band's cell and what moved in it.
"""

from collections.abc import Collection, Iterator, Mapping
from typing import Any, NamedTuple

import click

GLYPHS = {
    'forest': '♣',
    'grass': '"',
    'hills': '∩',
    'mountain': '▲',
    'outcrops': '▴',
    'water': '≈',
    'shallows': ':',
    'swamp': '%',
    'marsh': ',',
    'floodplain': '_',
    'desert': '.',
    'dunes': '∴',
    'tundra': '-',
    'snow': '*',
    'ice': '#',
}
RIVER = '~'
BAND = '@'
CAMP = 'Λ'
UNKNOWN = '  '
UNSEEN = '? '
LIT = (255, 0, 255)
CURSOR = (255, 215, 0)
HIDDEN = ('biome', 'river', 'x', 'y')
SHAPE = ('biomes', 'cells', 'rivers')
KNOWN = 'known'
STOCK = 'stock'
DIGITS = 3

type Rgb = tuple[int, int, int]
type Entry = dict[str, Any]


class Seen(NamedTuple):
    """
    One cell as the band knows it and as its stocks stand, with what each value moved by in the last update.
    """

    known: Entry | None
    stock: Entry | None
    known_moved: Entry
    stock_moved: Entry


def rgb(colour: str) -> Rgb:
    code = colour.lstrip('#')
    return int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)


def _ink(paper: Rgb) -> Rgb:
    red, green, blue = paper
    return (0, 0, 0) if 0.299 * red + 0.587 * green + 0.114 * blue > 128 else (255, 255, 255)


def glyph(biome: str) -> str:
    return GLYPHS.get(biome, biome[:1])


def pictured(
    known: Mapping[str, Any],
    colours: Mapping[str, str],
    band: tuple[int, int],
    lit: tuple[int, int] | None = None,
    cursor: tuple[int, int] | None = None,
    camps: Collection[tuple[int, int]] = (),
) -> Iterator[str]:
    """
    The rows of a map of what a band knows, cut to the cells it knows and those marked, each on its biome's
    colour; the band is @, a winter camp it built Λ, the lit target and the cursor stand on colours of their own.
    """
    width, height = known['width'], known['height']
    marks = {at: paper for at, paper in ((lit, LIT), (cursor, CURSOR)) if at is not None}
    places = [divmod(index, width) for index, cell in enumerate(known['cells']) if cell is not None]
    places += [
        (y - known['y'], x - known['x'])
        for x, y in marks
        if 0 <= x - known['x'] < width and 0 <= y - known['y'] < height
    ]
    if not places:
        return
    rows, columns = [row for row, _ in places], [column for _, column in places]
    for row in range(min(rows), max(rows) + 1):
        drawn = []
        for column in range(min(columns), max(columns) + 1):
            index = row * width + column
            cell = known['cells'][index]
            at = (known['x'] + column, known['y'] + row)
            mark = marks.get(at)
            if cell is None:
                drawn.append(UNKNOWN if mark is None else click.style(UNSEEN, bg=mark, fg=_ink(mark), bold=True))
                continue
            biome = known['biomes'][cell]
            here = at == band
            sign = BAND if here else CAMP if at in camps else glyph(biome)
            text = sign + (RIVER if known['rivers'][index] else ' ')
            paper = mark if mark is not None else rgb(colours[biome]) if biome in colours else None
            ink = None if paper is None else _ink(paper)
            drawn.append(click.style(text, bg=paper, fg=ink, bold=here or mark is not None))
        yield ''.join(drawn)


def _number(value: float) -> str:
    return f'{round(value, DIGITS):g}'


def _shown(value: Any) -> str:
    return _number(value) if isinstance(value, float) else str(value)


class Watched:
    """
    The cells as the band knows them and as their stocks stand, from a map and from the changes of updates.
    """

    def __init__(self) -> None:
        self.known: dict[tuple[int, int], Entry] = {}
        self.stocks: dict[tuple[int, int], Entry] = {}
        self._moved: dict[str, dict[tuple[int, int], Entry]] = {KNOWN: {}, STOCK: {}}

    def learn(self, known: Mapping[str, Any]) -> None:
        names = [name for name, value in known.items() if isinstance(value, list) and name not in SHAPE]
        width = known['width']
        for index, cell in enumerate(known['cells']):
            if cell is None:
                continue
            place = (known['x'] + index % width, known['y'] + index // width)
            entry = {'biome': known['biomes'][cell], 'river': bool(known['rivers'][index])}
            self.known[place] = entry | {name: known[name][index] for name in names}

    def stocked(self, rectangle: Mapping[str, Any]) -> None:
        """
        The stocks of a rectangle of the map as the game holds them, not as the band knows them.
        """
        names = [name for name, value in rectangle.items() if isinstance(value, list) and name not in SHAPE]
        width = rectangle['width']
        for index in range(len(rectangle['cells'])):
            place = (rectangle['x'] + index % width, rectangle['y'] + index // width)
            self.stocks[place] = {name: rectangle[name][index] for name in names}

    def take(self, changes: Mapping[str, Any]) -> None:
        """
        The cells of one update; what each value moved by is kept until the next update.
        """
        for title, kept, entries in (
            (KNOWN, self.known, changes.get('known', [])),
            (STOCK, self.stocks, changes.get('cells', [])),
        ):
            moved: dict[tuple[int, int], Entry] = {}
            for entry in entries:
                place = (entry['x'], entry['y'])
                before = kept.get(place, {})
                for name, value in entry.items():
                    if name not in HIDDEN and isinstance(before.get(name), float | int) and value != before[name]:
                        moved.setdefault(place, {})[name] = value - before[name]
                kept[place] = before | entry
            self._moved[title] = moved

    def cell(self, place: tuple[int, int]) -> Seen:
        return Seen(
            self.known.get(place),
            self.stocks.get(place),
            self._moved[KNOWN].get(place, {}),
            self._moved[STOCK].get(place, {}),
        )

    def said(self, band: Mapping[str, Any]) -> str:
        place = (band['place']['x'], band['place']['y'])
        seen = self.cell(place)
        told = [f'@ {place[0]},{place[1]}']
        if seen.known is not None:
            told.append(seen.known['biome'] + (' river' if seen.known['river'] else ''))
            told.append(self._values(KNOWN, seen.known, seen.known_moved))
        if seen.stock is not None:
            told.append(self._values(STOCK, seen.stock, seen.stock_moved))
        reason = band.get('reason')
        if reason:
            shown = (f'{name} {_shown(value)}' for name, value in reason.items() if value is not None)
            told.append('reason ' + ', '.join(shown))
        return ' | '.join(told)

    @staticmethod
    def _values(title: str, entry: Entry, moved: Entry) -> str:
        shown = []
        for name, value in entry.items():
            if name in HIDDEN or value is None:
                continue
            change = f' ({moved[name]:+.{DIGITS}g})' if name in moved else ''
            shown.append(f'{name} {_number(value)}{change}')
        return f'{title} ' + ', '.join(shown)
