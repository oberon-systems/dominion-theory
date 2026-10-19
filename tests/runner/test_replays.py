import gzip
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from dominion_theory.core.settings import Settings
from dominion_theory.runner import STEP, Service, read
from dominion_theory.runner.replays import UNFINISHED, UNREADABLE, played, summaries
from dominion_theory.store import ValkeyStore

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
}
DAY = 5
ACROSS = 20


@pytest.fixture
def service(tmp_path: Path) -> Service:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    return Service(ValkeyStore(raw, timedelta(hours=2)), Settings(records_dir=tmp_path))


def lived(service: Service, ticks: int, end: bool = True) -> Path:
    runner = service.create(seed=3, overrides=SMALL, mode=STEP)
    for _ in range(ticks):
        runner.step()
    if end:
        runner.end('died')
    return runner.record_path


def test_a_record_is_summed_up_by_its_length_its_end_and_its_people(service: Service, tmp_path: Path) -> None:
    path = lived(service, 3 * DAY)

    (found,) = summaries(tmp_path)

    assert (found.game, found.path, found.seed, found.seated) == (path.name.removesuffix('.jsonl.gz'), path, 3, False)
    assert (found.ticks, found.days, found.outcome) == (3 * DAY, 3, 'died')
    assert (found.start, found.most, found.born) == (15, 15, 0)
    assert found.days_a_year == 100


def test_a_game_cut_short_is_unfinished_and_a_broken_file_unreadable(service: Service, tmp_path: Path) -> None:
    lived(service, DAY, end=False)
    (tmp_path / 'alpha.jsonl.gz').write_bytes(b'not a record')

    found = {summary.game: summary.outcome for summary in summaries(tmp_path)}

    assert sorted(found.values()) == [UNFINISHED, UNREADABLE]
    assert found['alpha'] == UNREADABLE


def test_the_frames_of_a_record_carry_the_date_the_band_its_members_and_what_happened(service: Service) -> None:
    path = lived(service, 2 * DAY)

    game = played(path, ACROSS)

    assert game.exact is True
    assert [frame.tick for frame in game.frames] == list(range(1, 2 * DAY + 1))
    first, last = game.frames[0], game.frames[-1]
    assert first.date == {'year': 1, 'month': 1, 'day': 1, 'part': 'midday', 'season': 'spring'}
    assert first.counters['population'] == 15 and first.row is not None and first.row['people'] == 15
    assert first.band is not None and first.band['population'] == 15
    assert first.members is not None and len(first.members) == 15
    assert last.members is not None and last.band is not None
    assert any(event['key'] == 'day-started' for frame in game.frames for event in frame.events)
    assert game.lands.planet.biomes.shape == (ACROSS // 2, ACROSS)
    assert game.lands.biomes.shape == (16, 32)


def test_a_record_of_an_older_tree_is_drawn_by_its_planet_over_the_defaults(service: Service, tmp_path: Path) -> None:
    path = lived(service, DAY)
    lines = read(path)
    del lines[0]['params']['units']['band']['carry_water_kg']
    older = tmp_path / 'beta.jsonl.gz'
    older.write_bytes(gzip.compress(''.join(json.dumps(line) + '\n' for line in lines).encode()))

    game = played(older, ACROSS)

    assert game.exact is False
    assert game.params.planet.circumference_km == 4000
    assert len(game.frames) == DAY
