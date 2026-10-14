import json
from pathlib import Path

from dominion_theory.content import Params, load_params
from dominion_theory.planet import place
from dominion_theory.planet.tools import reference

REFERENCE = Path(__file__).with_name('maps.json')
SQUARE = 'the shore of the first window runs in square corners: water is cut by a grid, not by the land'
CORNERS = 4
STALE = 'the planet changed since its reference was written: make test redraws the maps and rewrites it'


def test_the_reference_is_the_one_of_this_planet() -> None:
    kept = json.loads(REFERENCE.read_text(encoding='utf-8'))

    assert kept['inputs'] == reference.inputs(load_params()), STALE
    assert sorted(kept['seeds']) == [str(seed) for seed in reference.SEEDS]
    assert sorted(kept['presets']) == sorted(reference.shaped(load_params()))
    for name, seeds in {'the default': kept['seeds'], **kept['presets']}.items():
        assert sorted(seeds) == [str(seed) for seed in reference.SEEDS]
        for seed, found in seeds.items():
            assert found['corners'] <= CORNERS, f'{name}, seed {seed}: {SQUARE}'


def test_presets_that_shape_the_planet_are_told_from_the_others() -> None:
    found = reference.shaped(load_params())

    assert {'pangea', 'continents', 'archipelago'} <= set(found)
    assert 'harsh-winter' not in found


def test_what_moved_between_two_surveys_is_told_by_path() -> None:
    old = {'1': {'rivers': 3, 'shares': {'water': 0.6, 'grass': 0.4}}}
    new = {'1': {'rivers': 3, 'shares': {'water': 0.5, 'grass': 0.4}}, '2': {'rivers': 1}}

    assert reference.moved(old, old) == []
    assert reference.moved(old, new) == ['1.shares.water: 0.6 -> 0.5', "2: None -> {'rivers': 1}"]


def test_a_survey_is_the_same_for_the_same_seed_and_can_be_written(params: Params) -> None:
    first = reference.survey(5, params)

    assert first == reference.survey(5, params)
    assert first != reference.survey(6, params)
    assert json.loads(json.dumps(first)) == first
    assert abs(sum(first['shares'].values()) - 1.0) < 1e-3
    assert first['window'] == [*place(5, params)]


def test_inputs_follow_the_parameters(params: Params) -> None:
    assert reference.inputs(params) == reference.inputs(params)
    assert reference.inputs(params) != reference.inputs(load_params())


def test_inputs_follow_only_what_shapes_the_planet() -> None:
    kept = reference.inputs(load_params())
    threat = 'biomes.forest.eras.band.properties.threat.base'
    fed = {'units.band.carry_kg': 7.0, 'council.status.start': 60, threat: 0.5}

    assert reference.inputs(load_params(overrides=fed)) == kept
    assert reference.inputs(load_params(overrides={'biomes.forest.generation.moisture': {'min': 0.6}})) != kept
    assert reference.inputs(load_params(overrides={'planet.sea': 0.5})) != kept


def test_inputs_follow_the_code_that_counts_the_reference() -> None:
    package = reference.PACKAGE
    counted = {package / 'planet' / 'tools' / 'pictures.py', package / 'planet' / 'tools' / 'reference.py'}

    assert counted | {package / 'content' / 'loader.py', package / 'planet' / 'rivers.py'} <= set(reference.SOURCES)
