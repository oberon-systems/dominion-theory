from contextlib import closing
from itertools import islice
from typing import Any

import pytest
from click.testing import CliRunner

from dominion_theory.client import Api, cli, follow, line

YEAR = 500
STEP_MODE = 'step'
WINDOW = 10
DAY = 5
EVENING = 3
# The cell north of where the band of seed 42 starts.
NORTHWARD = {'id': 'c-3', 'kind': 'vote', 'proposal': {'kind': 'go', 'to': {'x': 107, 'y': 46}}}
# A band that needs nothing, sees nothing and meets nothing: it camps, so the frame is tested alone.
QUIET = (
    'units.band.sight=0',
    'units.band.consumption_per_day.forage=0',
    'units.band.consumption_per_day.water=0',
    'units.band.people.birth.conceive_per_day=0',
    'units.band.people.injury.per_day=0',
    'units.band.people.age.per_year=0',
    'units.band.people.stages.adult.dies.frailty=0',
    'units.band.people.stages.adult.until.years=100',
    'encounters.chance=0',
)
PLANET = ('planet.circumference_km=4000', 'planet.window.width=32', 'planet.window.height=16')
SMALL = tuple(part for given in (*PLANET, *QUIET) for part in ('--set', given))
SIZE = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
# A voice that outweighs the whole band, so that what the player says is what the council does.
LOUD = {**SIZE, 'council.voice.least': 20.0}
SPOKEN = {
    'en': {
        4: (
            'morning, day 2, month 1, year 1, spring: 15 people, forage 15, water 15, camps. '
            'Command pass-4 was accepted. Day 2 of month 1, year 1, begins.'
        ),
        99: (
            'morning, day 1, month 3, year 1, summer: 15 people, forage 0, water 0, camps. '
            'Command pass-99 was accepted. '
            'Day 1 of month 3, year 1, begins. Month 3 of year 1 begins; the season is summer. '
            'Year 1: summer has come.'
        ),
        499: (
            'morning, day 1, month 1, year 2, spring: 15 people, forage 0, water 0, camps. '
            'Command pass-499 was accepted. '
            'Day 1 of month 1, year 2, begins. Month 1 of year 2 begins; the season is spring. '
            'Year 2: spring has come. Year 2 begins.'
        ),
    },
    'ru': {
        4: (
            'утро, день 2, месяц 1, год 1, весна: 15 человек, подножный корм 15, вода 15, стоит лагерем. '
            'Команда pass-4 принята. Начался день 2 месяца 1, год 1.'
        ),
        99: (
            'утро, день 1, месяц 3, год 1, лето: 15 человек, подножный корм 0, вода 0, стоит лагерем. '
            'Команда pass-99 принята. '
            'Начался день 1 месяца 3, год 1. Начался месяц 3 года 1; время года — лето. '
            'Год 1: наступило лето.'
        ),
        499: (
            'утро, день 1, месяц 1, год 2, весна: 15 человек, подножный корм 0, вода 0, стоит лагерем. '
            'Команда pass-499 принята. '
            'Начался день 1 месяца 1, год 2. Начался месяц 1 года 2; время года — весна. '
            'Год 2: наступила весна. Начался год 2.'
        ),
    },
}


@pytest.mark.parametrize('lang', ['en', 'ru'])
def test_a_game_year_is_played_printed_and_replayed(server: str, lang: str) -> None:
    runner = CliRunner()

    watched = runner.invoke(
        cli, ['watch', '--server', server, '--step', '--updates', str(YEAR), '--seed', '42', '--lang', lang, *SMALL]
    )
    lines = watched.stdout.splitlines()
    game = watched.stderr.split()[1]
    replayed = runner.invoke(cli, ['replay', '--server', server, game])

    assert watched.exit_code == 0
    assert len(lines) == YEAR
    assert {index: lines[index] for index in SPOKEN[lang]} == SPOKEN[lang]
    assert replayed.exit_code == 0
    assert replayed.stdout == f'the record of {game} replays: {YEAR} ticks, every hash matches\n'


COUNCIL = {
    'en': (
        'You turned the band: we go on through the forest.',
        'It came out even: we go on through the forest. Your standing stays 50.',
        'The votes: ',
    ),
    'ru': (
        'Вы повернули общину: идём по лесу.',
        'Ни хорошо, ни плохо: идём по лесу. Ваш вес остаётся 50.',
        'Голоса: ',
    ),
}


def played(api: Api, game: str, lang: str) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    band = api.snapshot(game)['units'][0]
    updates: list[dict[str, Any]] = []
    lines: list[str] = []
    actions: list[dict[str, Any]] = []
    with closing(api.updates(game, 0)) as stream:
        for update in islice(stream, WINDOW):
            band = follow(band, update)
            assert band is not None
            updates.append(update)
            lines.append(line(update, lang, band))
            actions.append(band['action'])
    return updates, lines, actions


@pytest.mark.parametrize('lang', ['en', 'ru'])
def test_a_vote_that_turns_the_band_sends_it_there_and_judges_it_on_arrival(api: Api, lang: str) -> None:
    called = api.create(STEP_MODE, 42, overrides=LOUD, seated=True)['id']
    for seq in range(WINDOW):
        api.command(called, NORTHWARD if seq == EVENING else {'id': f'pass-{seq}', 'kind': 'pass'})

    updates, lines, actions = played(api, called, lang)
    turned, judged, table = COUNCIL[lang]
    judging = EVENING + DAY - 1

    assert [action['kind'] for action in actions[EVENING : judging + 1]] == ['camp', 'camp', 'roam', 'move', 'gather']
    assert updates[EVENING]['changes']['seat'] == {'council': None}
    assert 'status' not in updates[judging]['changes']['seat']
    assert turned in lines[EVENING]
    assert judged in lines[judging] and table in lines[judging]
    assert api.snapshot(called)['seat']['seated'] is True
