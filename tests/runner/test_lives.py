import json
import math
from pathlib import Path

import pytest

from dominion_theory.content import load_params
from dominion_theory.runner import lives

REFERENCE = Path(__file__).with_name('lives.json')
STALE = 'the band changed since its reference was written: make test lives its seeds again and rewrites it'
SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}


def test_the_reference_is_the_one_of_this_band() -> None:
    kept = json.loads(REFERENCE.read_text(encoding='utf-8'))

    assert kept['inputs'] == lives.inputs(load_params()), STALE
    assert sorted(kept['seeds']) == [str(seed) for seed in lives.SEEDS]
    for life in kept['seeds'].values():
        assert [row['year'] for row in life['years']] == list(range(1, len(life['years']) + 1))
        assert life['outcome'] != lives.ALIVE or len(life['years']) == lives.YEARS
        assert all(row['snapshot'] > 0 for row in life['years'])
        assert len(life['hashes']) == len(life['years'])
    assert kept['first_year']['seeds'] == len(lives.FIRST)
    assert set(kept['first_year']['died']) <= {str(seed) for seed in lives.FIRST}


def test_inputs_follow_the_band_and_of_the_council_only_its_spread_and_the_status_it_starts_with() -> None:
    kept = lives.inputs(load_params())

    for council in ({'council.status.go_worked': 9}, {'council.status.abstained': -5}, {'council.voice.share': 0.9}):
        assert lives.inputs(load_params(overrides=council)) == kept
    band = ({'units.band.carry_kg': 7.0}, {'encounters.chance': 0.1}, {'planet.sea': 0.5})
    for changed in (*band, {'council.status.start': 60}, {'council.spread': 0.5}):
        assert lives.inputs(load_params(overrides=changed)) != kept
    assert {lives.PACKAGE / 'store' / 'codec.py', lives.PACKAGE / 'content' / 'loader.py'} <= set(lives.SOURCES)


def test_a_year_counts_every_tick_once_and_every_person_born_or_lost() -> None:
    life = lives.live(7, 1, overrides=SMALL)
    (year,) = life.years

    assert (life.outcome, life.start) == (lives.ALIVE, 15)
    assert year['moves'] + year['roams'] + year['gathers'] + year['camps'] + year['builds'] == life.tick
    assert year['growth'] == year['people'] - life.start == year['born'] - year['deaths']
    assert year['child'] == year['born'] - year['grown'] - year['child-deaths']
    assert life.growth == pytest.approx(year['people'] / life.start - 1)
    assert year['known'] > 0
    assert year['snapshot'] > 0
    assert len(life.hashes) == 1
    assert life.packing > 0


def test_the_same_seed_ends_every_year_in_the_same_state_and_another_seed_does_not() -> None:
    life = lives.live(7, 2, overrides=SMALL)

    assert lives.live(7, 2, overrides=SMALL).hashes == life.hashes
    assert lives.live(7, 2, overrides={**SMALL, 'council.status.go_worked': 9}).hashes == life.hashes
    assert lives.live(8, 2, overrides=SMALL).hashes != life.hashes


def test_growth_is_compounded_and_tells_the_year_of_a_tribe() -> None:
    doubled = lives.Lived(1, 15, [{'people': 30.0}], lives.ALIVE, 500)
    shrunk = lives.Lived(1, 15, [{'people': 12.0}], lives.ALIVE, 500)
    died = lives.Lived(1, 15, [{'people': 0.0}], 'died', 60)

    assert doubled.growth == pytest.approx(1.0)
    assert doubled.tribe == pytest.approx(1 + math.log(lives.TRIBE / 30) / math.log(2))
    assert shrunk.growth == pytest.approx(-0.2)
    assert (shrunk.tribe, died.growth, died.tribe) == (None, None, None)


def test_the_skills_are_told_by_the_day_they_were_learned() -> None:
    life = lives.Lived(1, 15, [], lives.ALIVE, 500, learned={'litters': 401, 'orientation': 354})

    assert life.lines()[-2] == 'learned: orientation on day 354, litters on day 401'
    assert lives.Lived(1, 15, [], lives.ALIVE, 500).lines()[-1].startswith('alive at tick 500')


def test_what_moved_between_two_references_is_told_by_path_and_year() -> None:
    old = {'1': {'outcome': 'alive', 'years': [{'people': 15}, {'people': 17}]}}
    new = {'1': {'outcome': 'died', 'years': [{'people': 15}]}}

    assert lives.moved(old, old) == []
    assert lives.moved(old, new) == ['1.outcome: alive -> died', "1.years.2: {'people': 17} -> None"]
