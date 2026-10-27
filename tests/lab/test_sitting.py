from pathlib import Path

import anyio
from mcp.types import CallToolResult, TextContent

from dominion_theory.client import Api
from dominion_theory.i18n import render
from dominion_theory.lab import dominion
from dominion_theory.lab.sitting import NO_COUNCIL, NO_GAME, NO_OPTION, SITS, STORY, Sitting
from dominion_theory.runner import replay

# A small planet, and a voice that outweighs the whole band, so that the first evening calls a council the seat
# may turn; no skill gates it.
LOUD = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'council.voice.least': 20.0,
    'skills': {},
}
# A band that needs nothing and meets nothing: after the first council no occasion calls another.
QUIET = {
    'units.band.sight': 0,
    'units.band.consumption_per_day.forage': 0,
    'units.band.consumption_per_day.water': 0,
    'units.band.decisions.weights.goods': 0,
    'units.band.people.birth.conceive_per_day': 0,
    'units.band.people.injury.per_day': 0,
    'units.band.people.age.per_year': 0,
    'units.band.people.stages.adult.dies.frailty': 0,
    'encounters.chance': 0,
}
TOOLS = ['new_game', 'look', 'council', 'vote', 'advance', 'panes', 'end']


def test_a_game_is_played_from_the_seat_to_its_end_and_its_record_replays(api: Api, tmp_path: Path) -> None:
    sitting = Sitting(api, LOUD)

    started = sitting.new_game(seed=42)
    advanced = sitting.advance()
    laid = sitting.council()
    assert sitting.session is not None and sitting.session.council is not None
    table = sitting.session.council['table']
    voted = sitting.vote(1)
    after = sitting.council()
    game = sitting.session.game
    ended = sitting.end()
    record = tmp_path / f'{game}.jsonl.gz'
    record.write_bytes(api.record(game))

    assert started.splitlines()[0] == f'Game {game}, seed 42.'
    assert 'Your standing is 50.' in started and '@' in started
    assert advanced.splitlines()[0] == render(STORY) and advanced.splitlines()[-1] == render(SITS)
    assert [line.split('.')[0] for line in laid.splitlines()[1:]] == [str(at) for at in range(1, len(table) + 2)] + [
        '0'
    ]
    assert laid.splitlines()[-2] == f'{len(table) + 1}. Say nothing'
    assert voted.splitlines()[0] == render(STORY)
    assert after == render(NO_COUNCIL)
    assert ended == f'Game {game} is over; make replay GAME={game} plays it back.'
    assert replay(record).matched


def test_the_seat_is_told_what_it_cannot_do(api: Api) -> None:
    sitting = Sitting(api, LOUD)
    unseated = [sitting.look(), sitting.council(), sitting.vote(1), sitting.advance(), sitting.panes(), sitting.end()]

    sitting.new_game(seed=42, lang='ru')
    early = sitting.vote(1)
    sitting.advance()
    assert sitting.session is not None and sitting.session.council is not None
    last = len(sitting.session.council['table']) + 1
    seq = sitting.session.seq
    waiting = sitting.advance()
    wrong = sitting.vote(last + 1)

    assert unseated == [render(NO_GAME)] * 6
    assert early == render(NO_COUNCIL, lang='ru')
    assert (waiting, sitting.session.seq) == (render(SITS, lang='ru'), seq)
    assert wrong == render(NO_OPTION, {'number': last + 1, 'last': last}, 'ru')


def test_advance_lives_the_days_asked_and_the_panes_tell_the_band(api: Api) -> None:
    sitting = Sitting(api, {**LOUD, **QUIET})
    sitting.new_game(seed=42)
    sitting.advance()
    assert sitting.session is not None and sitting.session.council is not None and sitting.session.date is not None
    sitting.vote(len(sitting.session.council['table']) + 1)
    before = dict(sitting.session.date)

    told = sitting.advance(days=2)
    panes = sitting.panes().splitlines()

    assert sitting.session.date['day'] == before['day'] + 2
    assert render(SITS) not in told
    assert panes[0].startswith('People: 15 people')
    assert panes[1] == 'Skills:'


def text(result: object) -> str:
    assert isinstance(result, CallToolResult) and isinstance(result.content[0], TextContent)
    return result.content[0].text


def test_the_server_offers_the_tools_of_the_seat_and_tells_a_refusal_in_words(api: Api) -> None:
    found = dominion.server(Sitting(api, LOUD))

    listed = anyio.run(found.list_tools)
    started = text(anyio.run(found.call_tool, 'new_game', {'seed': 42}))
    refused = text(anyio.run(found.call_tool, 'new_game', {'preset': 'alpha'}))

    assert [tool.name for tool in listed] == TOOLS
    assert all(tool.description for tool in listed)
    assert started.startswith('Game ')
    assert 'alpha' in refused
