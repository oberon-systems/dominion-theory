import hashlib
import json

import pytest
from pydantic import ValidationError

from dominion_theory.content import SCHEMA_VERSION, diff, load_params, presets
from dominion_theory.core.errors import DominionError


def months(preset: str | None = None, overrides: dict[str, object] | None = None) -> dict[str, int]:
    return {season.name: season.months for season in load_params(preset, overrides).time.seasons}


def refused(overrides: dict[str, object]) -> dict[str, object]:
    with pytest.raises(DominionError) as raised:
        load_params(overrides=overrides)

    assert raised.value.key == 'error-params-invalid'
    assert raised.value.values.keys() == {'path', 'found', 'expected'}
    return raised.value.values


def test_defaults_load() -> None:
    params = load_params()

    assert params.time.day_parts == ('morning', 'midday', 'afternoon', 'evening', 'night')
    assert params.time.days_per_month == 10
    assert months() == {'spring': 2, 'summer': 3, 'autumn': 2, 'winter': 3}
    assert params.eras['band'].parts_per_tick == 1
    assert params.eras.band is params.eras['band']
    assert params.schema_version == SCHEMA_VERSION


def test_planet_has_its_first_window() -> None:
    window = load_params().planet.window

    assert (window.width, window.height) == (512, 256)
    assert refused({'planet.window.width': 3})['path'] == 'planet.window.width'


def test_year_is_the_sum_of_its_seasons() -> None:
    params = load_params(overrides={'time.seasons.winter.months': 5})

    assert params.time.parts_per_day == 5
    assert params.time.months_per_year == 12
    assert params.time.days_per_year == 120


def test_unknown_era_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        _ = load_params().eras['alpha']


def test_tree_is_frozen() -> None:
    params = load_params()

    with pytest.raises(ValidationError):
        params.time.days_per_month = 12


def test_preset_changes_only_what_it_names() -> None:
    assert presets() == ['harsh-winter']
    assert months('harsh-winter') == {'spring': 2, 'summer': 2, 'autumn': 2, 'winter': 4}
    assert diff(load_params(), load_params('harsh-winter')) == {
        'time.seasons.summer.months': {'old': 3, 'new': 2},
        'time.seasons.winter.months': {'old': 3, 'new': 4},
    }


def test_unknown_preset_is_refused() -> None:
    with pytest.raises(DominionError) as raised:
        load_params('../defaults/time')

    assert raised.value.message() == {'key': 'error-preset-not-found', 'values': {'id': '../defaults/time'}}


def test_override_of_one_season_leaves_the_others() -> None:
    assert months(overrides={'time.seasons.autumn.months': 1}) == {'spring': 2, 'summer': 3, 'autumn': 1, 'winter': 3}


def test_override_is_laid_over_the_preset() -> None:
    assert months('harsh-winter', {'time.seasons.winter.months': 5, 'time.seasons.0.months': 1}) == {
        'spring': 1,
        'summer': 2,
        'autumn': 2,
        'winter': 5,
    }


def test_override_reaches_a_list_and_a_section() -> None:
    params = load_params(overrides={'time.day_parts': ['day', 'night'], 'eras.band': {'parts_per_tick': 2}})

    assert params.time.day_parts == ('day', 'night')
    assert params.eras.band.parts_per_tick == 2


@pytest.mark.parametrize(
    ('path', 'found', 'expected'),
    [
        ('units.band.population.start', 'units', 'one of eras, planet, time'),
        ('time.seasons.monsoon.months', 'monsoon', 'one of spring, summer, autumn, winter'),
        ('time.day_parts.9', '9', 'one of 0, 1, 2, 3, 4'),
        ('time.days_per_month.alpha', 'alpha', 'no name below a value'),
    ],
)
def test_unknown_path_is_refused_with_its_path(path: str, found: str, expected: str) -> None:
    assert refused({path: 20}) == {'path': path, 'found': found, 'expected': expected}


@pytest.mark.parametrize(
    ('path', 'value', 'where'),
    [
        ('time.days_per_month', 'ten', 'time.days_per_month'),
        ('time.days_per_month', 0, 'time.days_per_month'),
        ('time.seasons.winter', {'name': 'winter', 'months': 3, 'snow': 1}, 'time.seasons.winter.snow'),
        ('eras.band', {'parts_per_tick': 1, 'cell': 1}, 'eras.band.cell'),
        ('time.day_parts', ['Morning'], 'time.day_parts.0'),
    ],
)
def test_value_that_fails_the_schema_is_refused(path: str, value: object, where: str) -> None:
    values = refused({path: value})

    assert values['path'] == where
    assert values['expected']


def test_hash_is_the_sha256_of_the_canonical_tree() -> None:
    params = load_params()
    canonical = json.dumps(params.tree(), sort_keys=True, separators=(',', ':'))

    assert params.hash == hashlib.sha256(canonical.encode()).hexdigest()
    assert params.hash == load_params().hash
    assert params.hash == load_params(overrides={'time.days_per_month': 10}).hash


def test_hash_differs_when_a_value_differs() -> None:
    hashes = {
        load_params().hash,
        load_params('harsh-winter').hash,
        load_params(overrides={'time.days_per_month': 12}).hash,
    }

    assert len(hashes) == 3


def test_diff_names_the_changed_path() -> None:
    changed = load_params(overrides={'time.days_per_month': 12, 'eras.band.parts_per_tick': 5})

    assert diff(load_params(), load_params()) == {}
    assert diff(load_params(), changed) == {
        'eras.band.parts_per_tick': {'old': 1, 'new': 5},
        'time.days_per_month': {'old': 10, 'new': 12},
    }


def test_diff_names_an_item_that_came_or_went() -> None:
    longer = load_params(overrides={'time.day_parts': ['morning', 'midday', 'afternoon', 'evening', 'night', 'dusk']})

    assert diff(load_params(), longer) == {'time.day_parts.5': {'new': 'dusk'}}
    assert diff(longer, load_params()) == {'time.day_parts.5': {'old': 'dusk'}}
