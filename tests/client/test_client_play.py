from collections.abc import Generator, Mapping
from typing import Any

import click
import pytest
from click.testing import CliRunner

from dominion_theory.client import Api, Player, cli, menu
from dominion_theory.client.lines import SILENCE, Menu, way, where
from dominion_theory.client.player import RETURN, label, marked, pointed, understood
from dominion_theory.engine import council

type Body = dict[str, Any]

DATE = {'year': 1, 'month': 1, 'day': 1, 'part': 'morning', 'season': 'spring'}
SEAT = ['player']
STAY = {'kind': 'stay-and-gather'}
EAST = {'kind': 'go', 'to': {'x': 3, 'y': 0}}
NORTH = {'kind': 'go', 'to': {'x': 1, 'y': -2}}
COUNCIL: dict[str, Any] = {
    'leader': STAY,
    'table': [
        {'proposal': STAY, 'key': 'proposal-stay-and-gather', 'votes': 8},
        {'proposal': EAST, 'key': 'proposal-go-forest', 'votes': 5},
        {'proposal': NORTH, 'key': 'proposal-go-through-grass', 'votes': 1},
    ],
}
BAND = {
    'id': 1,
    'kind': 'band',
    'place': {'scale': 0, 'x': 1, 'y': 0},
    'population': 15,
    'stores': {'forage': 15.0, 'water': 15.0},
    'fatigue': 0.0,
    'states': [],
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
    'food': [0.5, 0.4],
}
STOCKED = {
    'scale': 0,
    'width': 1,
    'height': 1,
    'biomes': ['forest'],
    'cells': [0],
    'rivers': [1],
    'water': [1.0],
    'food': [0.75],
}
FOREST = {'biome': 'forest', 'river': False, 'water': 0.6, 'food': 0.5, 'threat': 0.2}
# The band stands in a forest that goes on north; east of it lies land it does not know.
WATCHED = {(1, 0): FOREST, (1, -2): FOREST}
SMALL = ('planet.circumference_km=4000', 'planet.window.width=32', 'planet.window.height=16')
# A voice that outweighs the whole band, so that what the player says is what the council does.
LOUD = tuple(part for given in (*SMALL, 'council.voice.least=20.0') for part in ('--set', given))


def update(seq: int, waiting: list[str] | None = None, seat: Body | None = None) -> Body:
    return {'seq': seq, 'date': DATE, 'events': [], 'changes': {'seat': seat or {}}, 'waiting': waiting or []}


class Scripted(Api):
    """
    Answers from a script instead of a server, and keeps the commands it was sent.
    """

    def __init__(self, messages: list[Body], council: Body | None = None) -> None:
        super().__init__()
        self.messages = messages
        self.council = council
        self.sent: list[Body] = []

    def snapshot(self, game_id: str) -> Body:
        seat = {'name': 'player', 'unit': 1, 'status': 50.0, 'seated': True, 'council': self.council}
        return {'seq': 3, 'seat': seat, 'units': [BAND], 'waiting': SEAT}

    def biomes(self, game_id: str) -> Body:
        return {'era': 'band', 'biomes': [{'id': 'forest', 'colour': '#006400'}]}

    def map(self, game_id: str, x: int, y: int, width: int, height: int, known: int | None = None) -> Body:
        if known is None:
            return {**STOCKED, 'x': x, 'y': y}
        return KNOWN

    def command(self, game_id: str, envelope: Body) -> Body:
        self.sent.append(envelope)
        return {'id': envelope['id'], 'taken': True}

    def updates(self, game_id: str, after: int) -> Generator[Body]:
        yield from self.messages


class Chooser:
    """
    Picks the place of a go by its number, or the answer by its number when there is no such place.
    """

    def __init__(self, picked: int) -> None:
        self.picked = picked
        self.asked: list[Menu] = []

    def __call__(self, given: Menu, lang: str) -> Mapping[str, Any]:
        self.asked.append(given)
        if self.picked < len(given.places):
            return dict(given.places[self.picked].proposal or {})
        return dict(given.answers[self.picked].proposal or SILENCE)


def test_the_menu_gives_the_answers_and_the_places_of_the_goes_best_first_the_leader_coloured() -> None:
    given = menu(COUNCIL, (1, 0), WATCHED.get)

    assert [(option.kind, option.proposal, option.leader) for option in given.answers] == [
        ('go', None, False),
        ('stay-and-gather', STAY, True),
        ('abstain', SILENCE, False),
    ]
    assert [label(option, 'en') for option in given.answers] == [
        'Roam',
        'Stay at the camp and gather',
        'Say nothing',
    ]
    assert marked(given.answers[1], 'en') == click.style('Stay at the camp and gather', fg='green', bold=True)
    assert marked(given.answers[0], 'en') == 'Roam'
    assert [label(option, 'ru') for option in given.places] == [
        'Идём в незнакомые земли, далеко',
        'Идём по лесу, далеко',
    ]
    assert given.place == (1, 0)


def test_what_the_voice_of_the_player_cannot_win_is_not_offered() -> None:
    heard = menu({**COUNCIL, 'voice': 3.75}, (1, 0), WATCHED.get)
    outweighed = {'leader': EAST, 'table': [{**COUNCIL['table'][0], 'votes': 1}, {**COUNCIL['table'][1], 'votes': 9}]}

    assert [option.proposal for option in heard.places] == [EAST]
    assert [option.kind for option in heard.answers] == ['go', 'stay-and-gather', 'abstain']
    assert [option.kind for option in menu({**outweighed, 'voice': 3.75}, (1, 0), WATCHED.get).answers] == [
        'go',
        'abstain',
    ]


def test_the_places_are_one_of_each_of_the_three_most_voted_the_leader_first_among_equals() -> None:
    goes = [council.going((x, 0)) for x in range(2, 8)]
    votes = (2, 5, 2, 5, 1, 0)
    table = [{'proposal': go, 'key': 'proposal-go', 'votes': held} for go, held in zip(goes, votes, strict=True)]

    given = menu({'leader': goes[3], 'table': table}, (1, 0), WATCHED.get)

    assert [option.proposal for option in given.places] == [goes[3], goes[0], goes[4]]
    assert [option.leader for option in given.places] == [True, False, False]


@pytest.mark.parametrize(
    ('cell', 'said'),
    [
        ({'biome': 'grass', 'river': False, 'threat': 0.1, 'food': 0.5}, 'We go to the safe meadows, far'),
        ({'biome': 'grass', 'river': True, 'threat': 0.5, 'food': 0.9}, 'We go to the dangerous meadows, far'),
        ({'biome': 'grass', 'river': True, 'threat': 0.2, 'food': 0.9}, 'We go to the meadows by the river, far'),
        ({'biome': 'grass', 'river': False, 'threat': 0.2, 'food': 0.6}, 'We go to the lush meadows, far'),
        ({'biome': 'grass', 'river': False, 'threat': 0.2, 'food': 0.5}, 'We go to the meadows, far'),
        (FOREST, 'We go on through the forest, far'),
        (None, 'We go into land we do not know, far'),
    ],
)
def test_a_place_is_told_by_its_land_and_whether_it_is_near(cell: Body | None, said: str) -> None:
    known = {(1, 0): FOREST, **({} if cell is None else {(3, 0): cell})}

    assert where(way((3, 0), (1, 0), known.get), 'en') == said


def test_a_place_next_to_the_band_is_near() -> None:
    assert where(way((2, 1), (1, 0), WATCHED.get), 'ru') == 'Идём в незнакомые земли, близко'


def test_a_seat_with_no_council_passes_every_wait() -> None:
    api = Scripted([update(4, SEAT), update(5)])
    chooser = Chooser(0)

    lines = list(Player(api, 'alpha', 'en', chooser).lines())

    assert [envelope['id'] for envelope in api.sent] == ['pass-3', 'pass-4']
    assert len(lines) == 2
    assert chooser.asked == []


def test_a_sitting_council_draws_the_map_and_sends_the_vote() -> None:
    api = Scripted([update(4, SEAT, {'council': None}), update(5)], COUNCIL)
    chooser = Chooser(0)

    lines = [click.unstyle(text) for text in Player(api, 'alpha', 'en', chooser).lines()]

    assert lines[:2] == ['♣ @~', 'Your standing is 50.']
    assert api.sent == [
        {'id': 'vote-3', 'kind': 'vote', 'proposal': EAST},
        {'id': 'pass-4', 'kind': 'pass'},
    ]
    assert len(chooser.asked) == 1


def test_the_updates_stop_at_the_limit() -> None:
    api = Scripted([update(4, SEAT), update(5, SEAT), update(6, SEAT)])

    lines = list(Player(api, 'alpha', 'en', Chooser(0)).lines(limit=2))

    assert len(lines) == 2
    assert [envelope['id'] for envelope in api.sent] == ['pass-3', 'pass-4']


def test_the_debug_line_follows_every_update() -> None:
    api = Scripted([update(4)])

    lines = list(Player(api, 'alpha', 'en', Chooser(0), debug=True).lines())

    assert click.unstyle(lines[1]) == '@ 1,0'


@pytest.mark.parametrize(
    ('answer', 'kind'),
    [
        ('1', 'go'),
        (' 2 ', 'stay-and-gather'),
        ('3', 'abstain'),
        ('', 'abstain'),
        ('abstain', 'abstain'),
        ('stay', 'stay-and-gather'),
        ('roam', 'go'),
        ('4', None),
        ('0', None),
        ('+3 -2', None),
        ('alpha', None),
    ],
)
def test_an_answer_is_a_number_a_name_or_nothing(answer: str, kind: str | None) -> None:
    chosen = understood(answer, menu(COUNCIL, (1, 0), WATCHED.get).answers)

    assert (None if chosen is None else chosen.kind) == kind


@pytest.mark.parametrize(
    ('answer', 'proposal'),
    [
        ('1', EAST),
        ('2', NORTH),
        ('3', None),
        ('', RETURN),
        ('+3 -2', {'kind': 'go', 'to': {'x': 4, 'y': -2}}),
        ('-1 0', {'kind': 'go', 'to': {'x': 0, 'y': 0}}),
        ('3 2', {'kind': 'go', 'to': {'x': 4, 'y': 2}}),
        ('+3', None),
        ('+-3 2', None),
        ('4', None),
        ('0', None),
        ('east', None),
    ],
)
def test_a_place_is_a_number_a_point_or_nothing_to_go_back(answer: str, proposal: Mapping[str, Any] | None) -> None:
    assert pointed(answer, menu(COUNCIL, (1, 0), WATCHED.get).places, (1, 0)) == proposal


def test_a_vote_from_the_terminal_turns_the_band_and_its_verdict_moves_the_status(server: str) -> None:
    played = CliRunner().invoke(
        cli,
        ['play', '--server', server, '--seed', '42', '--lang', 'en', '--updates', '8', '--debug', *LOUD],
        input='alpha\n1\n+0 -1\n',
    )
    lines = played.stdout.splitlines()
    north = 'we go on through the forest'

    assert played.exit_code == 0
    assert 'Not understood: alpha.' in lines
    assert 'Your standing is 50.' in lines
    assert any(f'You turned the band: {north}.' in text for text in lines)
    assert any(f'It went well: {north}. Your standing is now 54.' in text for text in lines)
    assert any('@ ' in text and not text.startswith('@ ') for text in lines)
    assert any(text.startswith('@ ') and '| reason ' in text for text in lines)


def test_silence_at_the_council_costs_standing(server: str) -> None:
    played = CliRunner().invoke(
        cli, ['play', '--server', server, '--seed', '42', '--lang', 'ru', '--updates', '4', *LOUD], input='\n'
    )

    assert played.exit_code == 0
    assert 'Вы промолчали на совете. Ваш вес теперь 48.' in played.stdout


def test_the_end_of_the_input_ends_the_game_quietly(server: str) -> None:
    played = CliRunner().invoke(cli, ['play', '--server', server, '--seed', '42', *LOUD], input='')

    assert played.exit_code == 0


def test_a_server_that_does_not_come_up_in_time_is_reported(unused_address: str) -> None:
    played = CliRunner().invoke(cli, ['play', '--server', unused_address, '--wait', '0.3'])

    assert played.exit_code == 1
    assert played.stderr.startswith('Error: ')


def test_the_debug_line_tells_the_band_cell_under_the_map() -> None:
    api = Scripted([], COUNCIL)

    lines = [click.unstyle(text) for text in Player(api, 'alpha', 'en', Chooser(0), debug=True).lines()]

    assert lines[:3] == [
        '♣ @~',
        '@ 1,0 | forest river | known food 0.4 | stock water 1, food 0.75',
        'Your standing is 50.',
    ]


def test_a_winter_camp_is_answered_only_while_the_council_offers_it() -> None:
    offered = menu({**COUNCIL, 'winter': True}, (1, 0), WATCHED.get)

    assert [option.kind for option in offered.answers] == ['go', 'stay-and-gather', 'winter-camp', 'abstain']
    assert label(offered.answers[2], 'en') == 'Make a winter camp here'
    assert understood('w', offered.answers) == offered.answers[2]
    assert [option.kind for option in menu(COUNCIL, (1, 0), WATCHED.get).answers] == [
        'go',
        'stay-and-gather',
        'abstain',
    ]
