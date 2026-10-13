import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from dominion_theory.content import LAYERS, RESOURCES, Modifier, Params, Range, diff, load_params, loader

FOOD = 'biomes.forest.eras.band.properties.food'


def test_defaults_hold_the_eight_biomes_in_generation_order() -> None:
    biomes = load_params().biomes

    assert sorted(biomes, key=lambda name: biomes[name].generation.order) == [
        'water',
        'mountain',
        'tundra',
        'outcrops',
        'hills',
        'desert',
        'forest',
        'grass',
    ]
    assert [name for name, biome in biomes.items() if not biome.generation.ranges] == ['grass']


def test_forest_is_the_one_of_its_document() -> None:
    forest = load_params().biomes['forest']
    food = forest.eras['band'].properties['food']

    assert forest.colour == '#006400'
    assert forest.generation.order == 70
    assert forest.generation.ranges == {'moisture': Range(min=0.5)}
    assert (food.base, food.recovery and food.recovery.model_dump()) == (0.9, {'days': 30})
    assert {season: (held.kind, held.amount) for season, held in food.seasons.items()} == {
        'spring': ('times', 0.7),
        'autumn': ('times', 1.2),
        'winter': ('times', 0.4),
    }
    assert forest.eras['band'].properties['threat'].recovery is None
    assert forest.eras['band'].resources == RESOURCES


def test_spot_checks_of_the_other_biomes() -> None:
    biomes = load_params().biomes
    water, desert = biomes['water'].eras['band'], biomes['desert']

    assert (water.properties['passability'].base, water.properties['water'].recovery) == (0.0, None)
    assert water.resources == ('water',)
    assert desert.generation.ranges == {'moisture': Range(max=0.15), 'temperature': Range(min=0.5)}
    assert desert.eras['band'].properties['food'].seasons == {}
    assert biomes['tundra'].eras['band'].properties['food'].seasons['summer'].amount == 1.5
    assert biomes['mountain'].generation.elevation == Range(min=0.88)
    assert biomes['grass'].eras['band'].properties['food'].model_dump()['recovery'] == {'days': 20}


def test_every_biome_gives_the_properties_of_the_era() -> None:
    params = load_params()

    assert params.eras.band.properties == ('water', 'food', 'threat', 'passability')
    assert params.eras.band.cell_km == 10
    for biome in params.biomes.values():
        assert set(biome.eras['band'].properties) == set(params.eras.band.properties)


def test_planet_is_the_one_of_the_document() -> None:
    planet = load_params().planet

    assert (planet.circumference_km, planet.skeleton_km, planet.sea) == (40000, 100, 0.6)
    assert planet.elevation.model_dump() == {'scale_km': 4000, 'octaves': 6, 'persistence': 0.6}
    assert planet.temperature.lapse == 0.4
    assert (planet.rivers.share, planet.rivers.meander_km) == (0.08, 30)
    assert planet.rivers.model_dump()['effects'] == {
        'band': {'water': {'plus': 0.5}, 'food': {'plus': 0.1}, 'passability': {'times': 0.7}}
    }
    assert (planet.window.x, planet.window.y, planet.window.tries) == (None, None, 64)
    assert planet.window.latitude.model_dump() == {'min': 0.3, 'max': 0.6}
    assert planet.window.needs.model_dump() == {
        'land': 0.6,
        'rivers': 1,
        'biomes': {'forest': 0.15, 'hills': 0.05, 'outcrops': 0.01},
    }


def test_override_reaches_a_base_and_a_season_modifier() -> None:
    params = load_params(overrides={f'{FOOD}.base': 0.5, f'{FOOD}.seasons.winter.times': 0.1})
    food = params.biomes['forest'].eras['band'].properties['food']

    assert (food.base, food.seasons['winter'].amount, food.seasons['spring'].amount) == (0.5, 0.1, 0.7)
    assert diff(load_params(), params) == {
        f'{FOOD}.base': {'old': 0.9, 'new': 0.5},
        f'{FOOD}.seasons.winter.times': {'old': 0.4, 'new': 0.1},
    }


def test_override_gives_a_season_another_kind_of_modifier() -> None:
    params = load_params(overrides={f'{FOOD}.seasons.winter': {'plus': -0.5}})
    winter = params.biomes['forest'].eras['band'].properties['food'].seasons['winter']

    assert (winter.kind, winter.amount) == ('plus', -0.5)


def test_preset_changes_one_biome_without_restating_the_others(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copytree(Path(str(loader.DATA)) / 'defaults', tmp_path / 'defaults')
    (tmp_path / 'presets').mkdir()
    preset = 'biomes:\n  desert:\n    eras:\n      band:\n        properties:\n          water: {base: 0.3}\n'
    (tmp_path / 'presets' / 'alpha.yaml').write_text(preset, encoding='utf-8')
    monkeypatch.setattr(loader, 'DATA', tmp_path)

    assert diff(load_params(), load_params('alpha')) == {
        'biomes.desert.eras.band.properties.water.base': {'old': 0.05, 'new': 0.3}
    }


def test_hash_changes_when_a_biome_changes() -> None:
    assert load_params().hash != load_params(overrides={'biomes.grass.colour': '#000000'}).hash
    assert load_params().hash == load_params(overrides={'biomes.grass.colour': '#228B22'}).hash


def test_resolved_tree_is_read_back_unchanged() -> None:
    params = load_params()

    assert Params.model_validate(params.tree()).hash == params.hash


@pytest.mark.parametrize('written', [{'plus': 0.1}, {'times': 0}, {'times': 2}, {'plus': -1}])
def test_modifier_is_one_of_two_kinds(written: dict[str, float]) -> None:
    assert Modifier.model_validate(written).model_dump() == written


@pytest.mark.parametrize('written', [{}, {'plus': 0.1, 'times': 1.0}, {'times': -0.1}, {'minus': 1.0}, {'plus': None}])
def test_modifier_is_refused(written: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Modifier.model_validate(written)


def test_range_is_closed_and_a_side_left_out_is_open() -> None:
    assert [Range(min=0.2, max=0.4).holds(value) for value in (0.1, 0.2, 0.4, 0.5)] == [False, True, True, False]
    assert Range(min=0.2).holds(1.0)
    assert Range(max=0.0).holds(-1.0)
    assert LAYERS == ('elevation', 'relief', 'moisture', 'temperature')
