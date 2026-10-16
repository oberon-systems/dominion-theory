from collections.abc import Generator, Mapping
from typing import Any

import click
import pytest
from click.testing import CliRunner

from dominion_theory.client import Api, Player, cli, options
from dominion_theory.client.lines import Option
from dominion_theory.client.player import SILENCE, understood

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
        {'proposal': EAST, 'key': 'proposal-go-east', 'votes': 5},
        {'proposal': NORTH, 'key': 'proposal-go-north', 'votes': 1},
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
    def __init__(self, picked: int) -> None:
        self.picked = picked
        self.asked: list[list[Option]] = []

    def __call__(self, listed: list[Option], lang: str, place: tuple[int, int] | None) -> Mapping[str, Any]:
        self.asked.append(listed)
        return listed[self.picked].proposal


def test_the_options_are_the_table_with_its_words_and_how_far_each_go_leads() -> None:
    listed = options(COUNCIL, (1, 0))
    silent = options({'leader': EAST, 'table': COUNCIL['table'][1:]})

    assert [option.proposal for option in listed] == [STAY, EAST, NORTH]
    assert [(option.votes, option.leader, option.far) for option in listed] == [
        (8, True, None),
        (5, False, 2),
        (1, False, 2),
    ]
    assert [option.key for option in listed] == ['proposal-stay-and-gather', 'proposal-go-east', 'proposal-go-north']
    assert silent[-1] == Option(STAY, 0, False, 'proposal-stay-and-gather')


def test_a_seat_with_no_council_passes_every_wait() -> None:
    api = Scripted([update(4, SEAT), update(5)])
    chooser = Chooser(0)

    lines = list(Player(api, 'alpha', 'en', chooser).lines())

    assert [envelope['id'] for envelope in api.sent] == ['pass-3', 'pass-4']
    assert len(lines) == 2
    assert chooser.asked == []


def test_a_sitting_council_draws_the_map_and_sends_the_vote() -> None:
    api = Scripted([update(4, SEAT, {'council': None}), update(5)], COUNCIL)
    chooser = Chooser(1)

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
    ('answer', 'proposal'),
    [
        ('2', EAST),
        (' 1 ', STAY),
        ('4', SILENCE),
        ('', SILENCE),
        ('abstain', SILENCE),
        ('+3 -2', {'kind': 'go', 'to': {'x': 4, 'y': -2}}),
        ('-1 0', {'kind': 'go', 'to': {'x': 0, 'y': 0}}),
        ('3 2', {'kind': 'go', 'to': {'x': 4, 'y': 2}}),
        ('+3', None),
        ('+-3 2', None),
        ('east', None),
        ('rest', None),
        ('stay', STAY),
        ('5', None),
        ('0', None),
        ('alpha', None),
    ],
)
def test_an_answer_is_a_number_a_name_a_point_or_nothing(answer: str, proposal: Mapping[str, Any] | None) -> None:
    assert understood(answer, options(COUNCIL, (1, 0)), (1, 0)) == proposal


def test_a_vote_from_the_terminal_turns_the_band_and_its_verdict_moves_the_status(server: str) -> None:
    played = CliRunner().invoke(
        cli,
        ['play', '--server', server, '--seed', '42', '--lang', 'en', '--updates', '8', '--debug', *LOUD],
        input='alpha\n+0 -1\n',
    )
    lines = played.stdout.splitlines()
    north = 'we go to the land towards the star that does not move'

    assert played.exit_code == 0
    assert 'Not understood: alpha.' in lines
    assert 'Your standing is 50.' in lines
    assert any(f'You turned the band: {north}.' in text for text in lines)
    assert any(f'It came out even: {north}. Your standing stays 50.' in text for text in lines)
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
