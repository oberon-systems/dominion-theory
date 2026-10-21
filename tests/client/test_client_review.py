import asyncio
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest
from textual.pilot import Pilot
from textual.widgets import DataTable, RichLog, Static

from dominion_theory.client.review import Games, Playback, Review, member, row
from dominion_theory.core.settings import Settings
from dominion_theory.runner import STEP, Service
from dominion_theory.runner.replays import Summary
from dominion_theory.store import ValkeyStore

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
}
DAY = 5
WITHIN = 200
PAUSE_S = 0.02
SIZE = (160, 50)
ELDER = {
    'age_days': 2150,
    'stage': 'elder',
    'sex': 'female',
    'player': False,
    'role': 'gatherer',
    'pregnant': False,
    'wound': 'light',
    'sick': True,
    'hungry': 0.0,
    'thirsty': 1.0,
    'kit': ['clothes'],
    'craft': {'spears': 0.67},
    'meat': 0.42,
}


@pytest.fixture
def records(tmp_path: Path) -> Path:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    service = Service(ValkeyStore(raw, timedelta(hours=2)), Settings(records_dir=tmp_path))
    runner = service.create(seed=3, overrides=SMALL, mode=STEP)
    for _ in range(2 * DAY):
        runner.step()
    runner.end('died')
    return tmp_path


async def until(pilot: Pilot[Any], met: Callable[[], bool]) -> None:
    for _ in range(WITHIN):
        if met():
            return
        await pilot.pause(PAUSE_S)
    raise AssertionError('the screen never got there')


def text(app: Review, name: str) -> str:
    return str(app.screen.query_one(f'#{name}', Static).content)


def test_a_member_is_told_by_sex_age_stage_role_how_it_fares_what_it_holds_and_eats() -> None:
    said = member(ELDER, 100, 'en')
    lean = member({**ELDER, 'meat': 0.0}, 100, 'en')

    assert said == (
        '♀ 21.5 y., elder, gatherer, lightly wounded, sick, thirsty, clothes, spears mastery 0.67, '
        'meat 0.42 of the ration'
    )
    assert lean == '♀ 21.5 y., elder, gatherer, lightly wounded, sick, thirsty, clothes, spears mastery 0.67'


def test_a_game_is_a_row_of_the_list_and_an_unreadable_one_says_so(tmp_path: Path) -> None:
    played = Summary('alpha', tmp_path, 0, 7, True, 640, 128, 'died', 15, 4, 19, 6, 17, 3, 41.5, 100)

    told = row(played, 'en')
    broken = row(Summary('beta', tmp_path, 0), 'en')

    assert told[0] == 'alpha' and told[2:] == [
        '7',
        'a player',
        '1y 28d',
        'the band died',
        '15 → 4 (most 19)',
        '6',
        '17',
        '3',
        '41.5',
    ]
    assert broken[0] == 'beta' and broken[5] == 'unreadable'


def test_the_list_opens_a_game_that_plays_pauses_steps_and_shows_its_people(records: Path) -> None:
    app = Review(records, 'en')
    seen: dict[str, Any] = {}

    async def reviewed() -> None:
        async with app.run_test(size=SIZE) as pilot:
            await until(pilot, lambda: isinstance(app.screen, Games))
            table = app.screen.query_one('#table', DataTable)
            await until(pilot, lambda: table.row_count == 1)
            seen['outcome'] = table.get_row_at(0)[5]
            await pilot.press('enter')
            await until(pilot, lambda: isinstance(app.screen, Playback))
            await pilot.press('space', 'home')
            seen['first'] = text(app, 'date')
            await pilot.press('right', 'i')
            await until(pilot, lambda: bool(app.screen.query_one('#detail').display))
            seen['detail'] = text(app, 'detail')
            seen['window'] = text(app, 'window')
            await pilot.press('end')
            seen['last'] = text(app, 'date')
            seen['log'] = [line.text for line in app.screen.query_one('#log', RichLog).lines]
            await pilot.press('q')
            await until(pilot, lambda: isinstance(app.screen, Games))
            await pilot.press('q')

    asyncio.run(reviewed())

    assert seen['outcome'] == 'the band died'
    assert seen['first'].startswith('midday, day 1, month 1, year 1, spring  paused')
    assert seen['detail'].startswith('15 people')
    assert seen['detail'].count('adult, gatherer') == 15
    assert '@' in seen['window']
    assert seen['last'].startswith('morning, day 3, month 1, year 1, spring')
    assert any('day 2' in line for line in seen['log'])
