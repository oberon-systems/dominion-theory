import click
import pytest
from click.testing import CliRunner, Result

from dominion_theory.client import Api, cli
from dominion_theory.client.cli import _overrides

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
SET = tuple(part for path, value in SMALL.items() for part in ('--set', f'{path}={value}'))


def run(*args: str) -> Result:
    return CliRunner().invoke(cli, args)


def test_overrides_are_read_as_values_and_as_text_otherwise() -> None:
    given = ('planet.window.width=32', 'council.part="evening"', 'alpha.beta=gamma=delta')

    assert _overrides(given) == {
        'planet.window.width': 32,
        'council.part': 'evening',
        'alpha.beta': 'gamma=delta',
    }


@pytest.mark.parametrize('item', ['alpha', '=7'])
def test_an_override_without_a_path_or_a_value_is_refused(item: str) -> None:
    with pytest.raises(click.BadParameter):
        _overrides((item,))


def test_a_real_time_game_is_created_watched_and_left_paused(server: str, api: Api) -> None:
    result = run('watch', '--server', server, '--updates', '3', '--seed', '42', *SET)
    game = api.game(result.stderr.split()[1])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        'day 1, month 1, year 1, spring: 15 people, forage 30.8, water 31, gathers forage (56%) and water (44%).',
        'day 1, month 1, year 1, spring: 15 people, forage 43.5, water 43.6, gathers forage (56%) and water (44%).',
        'day 1, month 1, year 1, spring: ' '15 people, forage 43.5, water 43.6, roams south, foraging on the way.',
    ]
    assert (game['seed'], game['mode'], game['running']) == (42, 'real-time', False)
    assert api.snapshot(game['id'])['seq'] >= 3


def test_a_game_is_joined_by_its_id_and_stepped(server: str, api: Api) -> None:
    game = api.create('step', seed=42, overrides=SMALL)['id']

    result = run('watch', '--server', server, '--game', game, '--step', '--updates', '2', '--lang', 'ru')

    assert result.exit_code == 0
    assert result.stderr == f'game {game}\n'
    assert result.stdout.splitlines() == [
        'день 1, месяц 1, год 1, весна: '
        '15 человек, подножный корм 30,8, вода 31, собирает подножный корм (56%) и воду (44%). Команда pass-0 принята.',
        'день 1, месяц 1, год 1, весна: '
        '15 человек, подножный корм 43,5, вода 43,6, собирает подножный корм (56%) и воду (44%). '
        'Команда pass-1 принята.',
    ]
    assert api.snapshot(game)['seq'] == 2


def test_a_refusal_is_said_in_the_language_asked_for(server: str) -> None:
    result = run('watch', '--server', server, '--game', 'alpha', '--lang', 'ru')

    assert result.exit_code == 1
    assert result.stdout == ''
    assert result.stderr == 'Error: Игра alpha не найдена.\n'


def test_a_server_that_is_not_there_is_an_error(unused_address: str) -> None:
    result = run('watch', '--server', unused_address)

    assert result.exit_code == 1
    assert result.stderr.startswith('Error: ')


def test_the_record_of_a_game_replays(server: str, api: Api) -> None:
    game = api.create('step', seed=42, overrides=SMALL)['id']
    run('watch', '--server', server, '--game', game, '--step', '--updates', '10')

    result = run('replay', '--server', server, game)

    assert result.exit_code == 0
    assert result.stdout == f'the record of {game} replays: 10 ticks, every hash matches\n'


def test_the_record_of_an_unknown_game_is_refused(server: str) -> None:
    result = run('replay', '--server', server, 'alpha')

    assert result.exit_code == 1
    assert result.stderr == 'Error: There is no game alpha.\n'


def test_a_band_with_no_food_is_lived_headless_into_a_row_for_its_last_year() -> None:
    hungry = (
        'units.band.gathering.forage=0',
        'units.band.start.stores.forage=0',
        'encounters.chance=0',
        'units.band.people.injury.per_day=0',
        'units.band.people.age.per_year=0',
        'units.band.people.stages.adult.dies.frailty=0',
        'units.band.people.stages.adult.until.years=100',
    )
    result = run('live', '--years', '3', '--seed', '42', *SET, *(part for item in hungry for part in ('--set', item)))

    assert result.exit_code == 0
    assert result.stderr == 'seed 42\n'
    header, row, end = result.stdout.splitlines()
    *counted, snapshot = row.split()
    assert len(header) == len(row)
    assert header.split() == [
        *('year', 'people', 'child', 'adult', 'elder', 'pregnant', 'injured', 'growth', 'rate', 'least', 'born'),
        *('grown', 'child-deaths'),
        *('deaths', 'of-hunger', 'of-thirst', 'of-encounter', 'of-age', 'of-frailty', 'of-birth'),
        *('food', 'water', 'moves', 'roams', 'gathers', 'camps', 'builds', 'starving', 'thirsty', 'tired'),
        *('encounters',),
        *('status', 'skills', 'hunters', 'sick'),
        *('known', 'snapshot'),
    ]
    assert counted == [
        '1',
        '0',
        '0',
        '0',
        '0',
        '0',
        '0',
        '-15',
        '-100',
        '0',
        '0',
        '0',
        '0',
        '14',
        '14',
        '0',
        '0',
        '0',
        '0',
        '0',
        '0',
        '0',
        '0',
        '1',
        '5',
        '4',
        '0',
        '5',
        '0',
        '0',
        '0',
        '50',
        '0',
        '0',
        '0',
        '0',
    ]
    assert float(snapshot) > 0
    assert end == 'died at tick 10: no growth, 150 people never, 0 of 0 children grew up'
