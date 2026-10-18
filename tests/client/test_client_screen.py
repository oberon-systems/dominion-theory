import asyncio
from collections.abc import Callable, Generator
from typing import Any

from textual.pilot import Pilot
from textual.widgets import RichLog, Static

from dominion_theory.client import Api, Screen, Session
from dominion_theory.client.screen import ended

type Body = dict[str, Any]

DATE = {'year': 1, 'month': 1, 'day': 1, 'part': 'midday', 'season': 'spring'}
STAY = {'kind': 'stay-and-gather'}
EAST = {'kind': 'go', 'to': {'x': 3, 'y': 0}}
COUNCIL = {
    'leader': STAY,
    'table': [
        {'proposal': STAY, 'key': 'proposal-stay-and-gather', 'votes': 8},
        {'proposal': EAST, 'key': 'proposal-go-forest', 'votes': 5},
    ],
}
BAND = {
    'id': 1,
    'kind': 'band',
    'place': {'scale': 0, 'x': 1, 'y': 0},
    'population': 15,
    'stores': {'forage': 15.0, 'water': 15.0},
    'fatigue': 0.0,
    'states': ['thirst'],
    'action': {'kind': 'camp'},
    'intent': None,
    'reason': None,
}
KNOWN = {
    'scale': 0,
    'x': 0,
    'y': 0,
    'width': 2,
    'height': 1,
    'biomes': ['forest'],
    'cells': [0, 0],
    'rivers': [0, 1],
    'water': [0.6, 0.6],
    'food': [0.9, 0.5],
}
TURNED = {'key': 'council-turned', 'values': {'proposal': 'proposal-go-forest', 'yes': 9.0, 'all': 14.0}}
ACCEPTED = {'key': 'command-accepted', 'values': {'id': 'vote-3'}}
UPDATES = [
    {
        'seq': 4,
        'date': DATE,
        'events': [ACCEPTED, TURNED],
        'changes': {'seat': {'council': None}},
        'waiting': ['player'],
    },
    {'seq': 5, 'date': DATE, 'events': [], 'changes': {}, 'waiting': []},
]
SAID = 'day 1, month 1, year 1, spring: ' 'You turned the band: we go into the forest. 9 voices of 14 were for it.'
WITHIN = 200
# A terminal low enough that an opened pane would push the council off it.
SMALL = (120, 24)
PAUSE_S = 0.02


class Scripted(Api):
    """
    A game at its first council, answered from a script.
    """

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[Body] = []

    def snapshot(self, game_id: str) -> Body:
        seat = {'name': 'player', 'unit': 1, 'status': 50.0, 'seated': True, 'council': COUNCIL}
        return {'seq': 3, 'date': DATE, 'seat': seat, 'units': [BAND], 'waiting': ['player']}

    def biomes(self, game_id: str) -> Body:
        name = {'key': 'biome-forest', 'values': {}}
        return {'era': 'band', 'biomes': [{'id': 'forest', 'name': name, 'colour': '#006400'}]}

    def params(self, game_id: str) -> Body:
        return {'skills': {'orientation': {}, 'wintering': {}, 'sticks': {}}}

    def map(self, game_id: str, x: int, y: int, width: int, height: int, known: int | None = None) -> Body:
        return KNOWN

    def command(self, game_id: str, envelope: Body) -> Body:
        self.sent.append(envelope)
        return {'id': envelope['id'], 'taken': True}

    def updates(self, game_id: str, after: int) -> Generator[Body]:
        yield from UPDATES


async def until(pilot: Pilot[Any], met: Callable[[], bool]) -> None:
    for _ in range(WITHIN):
        if met():
            return
        await pilot.pause(PAUSE_S)
    raise AssertionError('the screen never got there')


def text(screen: Screen, name: str) -> str:
    return str(screen.query_one(f'#{name}', Static).content)


def test_the_screen_draws_the_band_and_its_place_and_sends_the_vote_picked_in_the_menu() -> None:
    api = Scripted()
    screen = Screen(Session(api, 'alpha'), 'en', pace=0)
    seen: dict[str, Any] = {}

    async def played() -> None:
        async with screen.run_test(size=(140, 40)) as pilot:
            await until(pilot, lambda: bool(screen.query_one('#council').display))
            seen['map'], seen['band'], seen['cell'] = text(screen, 'map'), text(screen, 'band'), text(screen, 'cell')
            seen['answers'] = text(screen, 'question')
            await pilot.press('up', 'enter')
            await until(pilot, lambda: 'Where' in text(screen, 'question'))
            seen['places'] = str(screen.query_one('#cell').border_title)
            await pilot.press('enter')
            await until(pilot, lambda: len(api.sent) == 2)
            await until(pilot, lambda: 'over' in text(screen, 'question'))
            seen['log'] = [line.text for line in screen.query_one('#log', RichLog).lines]
            await pilot.press('q')

    asyncio.run(played())

    assert seen['map'] == '♣ @~'
    assert seen['band'].splitlines() == ['15 people', 'thirst', 'camps', 'fatigue 0', 'Your standing is 50.']
    assert seen['cell'].splitlines()[:2] == ['forest, a river', 'water        ██████░░░░ 0.6']
    assert seen['answers'].startswith('What do you say at the council?')
    assert seen['places'] == 'The target'
    assert api.sent == [
        {'id': 'vote-3', 'kind': 'vote', 'proposal': EAST},
        {'id': 'pass-4', 'kind': 'pass'},
    ]
    assert ''.join(seen['log']).replace(' ', '') == SAID.replace(' ', '')
    assert screen.return_value is None


def test_a_cell_picked_with_the_cursor_on_the_map_is_where_the_band_is_sent() -> None:
    api = Scripted()
    screen = Screen(Session(api, 'alpha'), 'en', pace=0)
    seen: dict[str, Any] = {}

    async def played() -> None:
        async with screen.run_test(size=(140, 40)) as pilot:
            await until(pilot, lambda: bool(screen.query_one('#council').display))
            await pilot.press('up', 'enter')
            await until(pilot, lambda: 'Where' in text(screen, 'question'))
            await pilot.press('down', 'enter')
            await until(pilot, lambda: 'Arrows' in text(screen, 'question'))
            await pilot.press('enter', 'left', 'h')
            seen['title'], seen['cell'] = str(screen.query_one('#cell').border_title), text(screen, 'cell')
            await pilot.press('enter')
            await until(pilot, lambda: len(api.sent) == 2)
            await pilot.press('q')

    asyncio.run(played())

    assert (seen['title'], seen['cell'].splitlines()[0]) == ('The target', 'forest')
    assert api.sent[0] == {'id': 'vote-3', 'kind': 'vote', 'proposal': {'kind': 'go', 'to': {'x': 0, 'y': 0}}}


class Learned(Scripted):
    """
    The same council, of a band that has learned two skills, holds goods and has children.
    """

    def snapshot(self, game_id: str) -> Body:
        held = super().snapshot(game_id)
        band = {
            **BAND,
            'lore': ['orientation', 'sticks'],
            'goods': {'sticks': 4.5},
            'ages': {'child': 3, 'adult': 12, 'elder': 0},
            'pregnant': 2,
        }
        return {**held, 'units': [band]}


class Agreed(Scripted):
    """
    A game whose evening council is settled and does not sit.
    """

    def snapshot(self, game_id: str) -> Body:
        held = super().snapshot(game_id)
        return {**held, 'seat': {**held['seat'], 'council': None}}

    def updates(self, game_id: str, after: int) -> Generator[Body]:
        values = {'leader': 'proposal-stay-and-gather', 'occasion': 'occasion-first'}
        agreed = {'key': 'council-agreed', 'values': values}
        yield {'seq': 4, 'date': DATE, 'events': [agreed], 'changes': {}, 'waiting': ['player']}
        yield {'seq': 5, 'date': DATE, 'events': [], 'changes': {}, 'waiting': []}


def test_the_skills_the_stores_and_the_people_open_by_their_keys_and_close_again() -> None:
    api = Learned()
    screen = Screen(Session(api, 'alpha'), 'en', pace=0)
    seen: dict[str, Any] = {}

    async def played() -> None:
        async with screen.run_test(size=SMALL) as pilot:
            await until(pilot, lambda: bool(screen.query_one('#council').display))
            for key in ('r', 's', 'i'):
                await pilot.press(key)
                seen[key] = (str(screen.query_one('#detail').border_title), text(screen, 'detail'))
                seen[f'{key}-foot'] = screen.query_one('#council').region.bottom
            await pilot.press('i')
            seen['closed'] = screen.query_one('#detail').display
            seen['council'] = screen.query_one('#council').display
            await pilot.press('q')

    asyncio.run(played())

    assert seen['r'] == ('Skills', '✓ to find its way\n· to winter\n✓ to cut sticks')
    assert seen['s'] == ('Stores', 'forage 15\nwater 15\nsticks 4.5')
    assert seen['i'] == ('People', '15 people\n3 children\n12 adults\n2 with child')
    assert (seen['closed'], seen['council']) == (False, True)
    assert max(seen[f'{key}-foot'] for key in 'rsi') <= SMALL[1]


def test_an_evening_with_no_council_waits_until_the_day_is_read() -> None:
    api = Agreed()
    screen = Screen(Session(api, 'alpha'), 'en', pace=0)
    seen: dict[str, Any] = {}

    async def played() -> None:
        async with screen.run_test(size=(140, 40)) as pilot:
            await until(pilot, lambda: 'day is over' in text(screen, 'question'))
            seen['waiting'] = list(api.sent)
            await pilot.press('enter')
            await until(pilot, lambda: 'game is over' in text(screen, 'question') and len(api.sent) == 2)
            await pilot.press('q')

    asyncio.run(played())

    assert seen['waiting'] == [{'id': 'pass-3', 'kind': 'pass'}]
    assert api.sent == [{'id': 'pass-3', 'kind': 'pass'}, {'id': 'pass-4', 'kind': 'pass'}]


def test_the_end_of_a_game_says_why() -> None:
    def session(status: float, band: Body | None) -> Any:
        return type('Told', (), {'status': status, 'band': band})()

    assert ended(session(0.0, BAND)) == 'play-over-banished'
    assert ended(session(12.5, None)) == 'play-over-died'
    assert ended(session(12.5, BAND)) == 'play-over'
