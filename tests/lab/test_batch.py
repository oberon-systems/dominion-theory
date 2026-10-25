import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from dominion_theory.core.errors import DominionError
from dominion_theory.core.settings import Settings
from dominion_theory.lab import Planned, Run, load, report
from dominion_theory.lab.batch import REPORT, SUMMARY, batch, play
from dominion_theory.lab.report import COLUMNS
from dominion_theory.runner import CAP, DIED, REACHED, read

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
TINY: dict[str, Any] = {
    'lands': [1, 2],
    'draws': 2,
    'until': {'people': 150, 'years': 0.3},
    'workers': 2,
    'players': ['leader', 'greedy'],
    'params': {'small': {'overrides': SMALL}},
    'records': 1,
}
NIGHT = Path(__file__).parents[2] / 'lab' / 'runs' / 'night.yaml'


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(records_dir=tmp_path / 'records')


def told(run: Run, out: Path, settings: Settings) -> list[str]:
    said: list[str] = []
    out.mkdir(exist_ok=True)
    batch(run, 'tiny', out, settings, said.append)
    return said


def test_a_tiny_run_plays_every_game_into_a_summary_a_report_and_the_records_asked(
    tmp_path: Path, settings: Settings
) -> None:
    run = Run.model_validate(TINY)
    out = tmp_path / 'tiny'

    said = told(run, out, settings)
    lines = [json.loads(text) for text in (out / SUMMARY).read_text().splitlines()]
    kept = sorted(settings.records_dir.iterdir())

    assert said[0] == 'tiny: 2 lands, 2 draws, 2 players, 1 sets: 8 games, 8 to play, 2 workers'
    assert len(said) == 1 + 4 and all(', small: 2 games, 0 reached 150, ' in line for line in said[1:])
    assert sorted((line['land'], line['draw'], line['player']) for line in lines) == sorted(
        (land, draw, player) for land in (1, 2) for draw in (0, 1) for player in ('leader', 'greedy')
    )
    assert {line['outcome'] for line in lines} == {CAP}
    assert all(line['councils']['sat'] >= 1 and line['people']['start'] > 0 for line in lines)
    assert all(line['councils']['turned'] == 0 for line in lines if line['player'] == 'leader')
    assert sorted(line['record'] for line in lines if line['record']) == [path.name.split('.')[0] for path in kept]
    assert sorted(read(path)[0]['seats'][0]['kind'] for path in kept) == ['greedy', 'greedy', 'leader', 'leader']
    assert {read(path)[0]['draw'] for path in kept} == {0}
    shown = (out / REPORT).read_text().splitlines()
    assert shown[0] == 'tiny: 8 of 8 games'
    assert shown[2].split() == ['small', *COLUMNS]
    assert [row.split()[:2] for row in shown[3:5]] == [['leader', '4'], ['greedy', '4']]
    assert 'land 2 greedy' in '\n'.join(shown)


def test_a_finished_run_resumed_plays_nothing_more(tmp_path: Path, settings: Settings) -> None:
    run = Run.model_validate({**TINY, 'lands': [1], 'workers': 1})
    out = tmp_path / 'tiny'
    told(run, out, settings)
    before = (out / SUMMARY).read_text()

    said = told(run, out, settings)

    assert said == ['tiny: 1 lands, 2 draws, 2 players, 1 sets: 4 games, 0 to play, 1 workers']
    assert (out / SUMMARY).read_text() == before


def test_a_run_cut_short_plays_only_the_games_its_summary_lacks(tmp_path: Path, settings: Settings) -> None:
    run = Run.model_validate({**TINY, 'lands': [1], 'workers': 1})
    out = tmp_path / 'tiny'
    out.mkdir()
    first = play(Planned(1, 0, 'leader', 'small'), run, settings)
    (out / SUMMARY).write_text(json.dumps(first) + '\n')

    said = told(run, out, settings)
    lines = [json.loads(text) for text in (out / SUMMARY).read_text().splitlines()]

    assert said[0].endswith('4 games, 3 to play, 1 workers')
    assert len(lines) == 4 and lines[0] == first


@pytest.mark.parametrize(('until', 'outcome', 'day'), [({'years': 0.1}, CAP, 10), ({'people': 10}, REACHED, 0)])
def test_the_cap_of_years_or_the_goal_ends_a_game(
    settings: Settings, until: dict[str, Any], outcome: str, day: int
) -> None:
    run = Run.model_validate({**TINY, 'until': until, 'records': 0})

    line = play(Planned(1, 0, 'greedy', 'small'), run, settings)

    assert (line['outcome'], line['day'], line['record']) == (outcome, day, None)
    assert not settings.records_dir.exists() or list(settings.records_dir.iterdir()) == []


def test_the_run_file_names_lands_players_and_their_draws() -> None:
    night = load(NIGHT)
    players = ['leader', {'mind': 'linear_v0', 'draws': 1}]
    run = Run.model_validate({**TINY, 'lands': {'first': 3, 'count': 2}, 'players': players})

    assert len(night.planned()) == 10 * 50 * 4 * 2
    assert run.seeds == [3, 4]
    assert run.seated == [('leader', 'leader', 2), ('linear_v0', {'mind': 'linear_v0'}, 1)]
    assert [held.key for held in run.planned()] == [
        (3, 0, 'leader', 'small'),
        (3, 1, 'leader', 'small'),
        (3, 0, 'linear_v0', 'small'),
        (4, 0, 'leader', 'small'),
        (4, 1, 'leader', 'small'),
        (4, 0, 'linear_v0', 'small'),
    ]


@pytest.mark.parametrize(
    'changed',
    [
        {'players': ['leader', 'leader']},
        {'players': ['alpha']},
        {'players': [{'mind': 'beta'}]},
        {'draws': 0},
        {'lands': []},
        {'until': {'years': 0}},
        {'seats': 1},
    ],
)
def test_a_run_file_that_asks_the_impossible_is_refused(changed: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Run.model_validate({**TINY, **changed})


def test_a_set_of_parameters_that_fails_its_check_is_refused_with_the_run() -> None:
    with pytest.raises(DominionError):
        Run.model_validate({**TINY, 'params': {'alpha': {'overrides': {'time.days_per_month': 0}}}})


def line(player: str, draw: int, outcome: str, day: int, end: int, **fields: Any) -> dict[str, Any]:
    return {
        'land': 1,
        'draw': draw,
        'player': player,
        'set': 'small',
        'outcome': outcome,
        'day': day,
        'people': {'start': 10, 'end': end, 'most': end},
        'councils': {'sat': 10, 'turned': fields.get('turned', 0)},
        'verdicts': {'worked': fields.get('worked', 0), 'even': 0, 'failed': fields.get('failed', 0)},
        'skills': fields.get('skills', {}),
        'causes': fields.get('causes', {}),
        'occasions': {'first': 1},
    }


def test_the_report_measures_the_goal_and_the_gain_over_the_leader() -> None:
    run = Run.model_validate({**TINY, 'lands': [1]})
    lines = [
        line('leader', 0, CAP, 200, 40),
        line('leader', 1, DIED, 50, 0, causes={'hunger': 10}),
        line('greedy', 0, REACHED, 150, 150, turned=4, worked=3, failed=1, skills={'sticks': 0}),
        line('greedy', 1, CAP, 200, 90, turned=2),
    ]

    shown = report('alpha', run, lines, {'small': 100}, 8)

    assert shown[:2] == ['alpha: 4 of 8 games', '']
    assert shown[3].split() == ['leader', '2', '0.0%', '-', '+100.0%', '4', '50.0%', '50.0%', '0.0%', '-', '-', '-']
    assert shown[4].split() == [
        'greedy',
        '2',
        '50.0%',
        '150',
        '+200.0%',
        '3',
        '0.0%',
        '0.0%',
        '30.0%',
        '75.0%',
        '+50.0%',
        '+100.0%',
    ]
    assert ['sticks', '0%', '50%'] in [row.split() for row in shown]
    assert ['hunger', '5.0', '0.0'] in [row.split() for row in shown]
