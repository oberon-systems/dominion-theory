import pytest
from click.testing import CliRunner

from dominion_theory.client import cli

YEAR = 500
SMALL = ('--set', 'planet.circumference_km=4000', '--set', 'planet.window.width=32', '--set', 'planet.window.height=16')
SPOKEN = {
    'en': {
        4: 'morning, day 2, month 1, year 1, spring: Command pass-4 was accepted. Day 2 of month 1, year 1, begins.',
        99: (
            'morning, day 1, month 3, year 1, summer: Command pass-99 was accepted. '
            'Day 1 of month 3, year 1, begins. Month 3 of year 1 begins; the season is summer. '
            'Year 1: summer has come.'
        ),
        499: (
            'morning, day 1, month 1, year 2, spring: Command pass-499 was accepted. '
            'Day 1 of month 1, year 2, begins. Month 1 of year 2 begins; the season is spring. '
            'Year 2: spring has come. Year 2 begins.'
        ),
    },
    'ru': {
        4: 'утро, день 2, месяц 1, год 1, весна: Команда pass-4 принята. Начался день 2 месяца 1, год 1.',
        99: (
            'утро, день 1, месяц 3, год 1, лето: Команда pass-99 принята. '
            'Начался день 1 месяца 3, год 1. Начался месяц 3 года 1; время года — лето. '
            'Год 1: наступило лето.'
        ),
        499: (
            'утро, день 1, месяц 1, год 2, весна: Команда pass-499 принята. '
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
