from contextlib import closing
from itertools import islice
from typing import Any

import pytest
from click.testing import CliRunner

from dominion_theory.client import Api, cli, follow, line

YEAR = 500
STEP_MODE = 'step'
WINDOW = 10
STAY = {'id': 'c-1', 'kind': 'call-council', 'proposal': {'kind': 'stay-and-gather'}}
# A band that needs nothing, sees nothing and meets nothing: it camps, so the frame is tested alone.
QUIET = (
    'units.band.sight=0',
    'units.band.consumption_per_day.forage=0',
    'units.band.consumption_per_day.water=0',
    'units.band.population.growth_per_year=0',
    'encounters.chance=0',
)
PLANET = ('planet.circumference_km=4000', 'planet.window.width=32', 'planet.window.height=16')
SMALL = tuple(part for given in (*PLANET, *QUIET) for part in ('--set', given))
SIZE = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
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
        'midday, day 1, month 1, year 1, spring: 15 people, forage 43.4, water 15, gathers forage. '
        'Command c-1 was accepted. The council agreed: we stay, we are short of food. 17.8 voices of 17.8 were for it.',
        'morning, day 3, month 1, year 1, spring: 15 people, forage 38.6, water 21.4, camps. Your standing is 53. '
        'Command pass-9 was accepted. It went well: we stay, we are short of food. Your standing is now 53. '
        'Day 3 of month 1, year 1, begins.',
    ),
    'ru': (
        'полдень, день 1, месяц 1, год 1, весна: 15 человек, подножный корм 43,4, вода 15, собирает подножный корм. '
        'Команда c-1 принята. Совет согласился: остаёмся: нам не хватает еды. За — 17,8 голосов из 17,8.',
        'утро, день 3, месяц 1, год 1, весна: 15 человек, подножный корм 38,6, вода 21,4, стоит лагерем. Ваш вес 53. '
        'Команда pass-9 принята. Всё вышло хорошо: остаёмся: нам не хватает еды. Ваш вес теперь 53. '
        'Начался день 3 месяца 1, год 1.',
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
def test_a_proposal_bends_the_band_and_its_verdict_moves_the_status(api: Api, lang: str) -> None:
    called, free = (api.create(STEP_MODE, 42, overrides=SIZE)['id'] for _ in range(2))
    api.command(called, STAY)
    api.command(free, {'id': 'pass-0', 'kind': 'pass'})
    for seq in range(1, WINDOW):
        for game in (called, free):
            api.command(game, {'id': f'pass-{seq}', 'kind': 'pass'})

    updates, lines, actions = played(api, called, lang)
    alone = played(api, free, lang)[2]

    assert {action['kind'] for action in actions} <= {'gather', 'camp'}
    assert 'move' in {action['kind'] for action in alone}
    assert actions != alone
    assert updates[0]['changes']['seat'] == {'council_from': WINDOW}
    assert updates[-1]['changes']['seat'] == {'status': 53.0}
    assert (lines[0], lines[-1]) == COUNCIL[lang]
    assert api.snapshot(called)['seat']['status'] == 53.0
