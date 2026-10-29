from typing import Any

import numpy as np
import pytest

from dominion_theory.content import FEATURES, Mind, Params, load_params
from dominion_theory.engine import Game, Observation, Option, Window, observe
from dominion_theory.engine import band as bands
from dominion_theory.engine.observation import MEASURES, Ground, _winter_left, choose, features, scores
from dominion_theory.engine.streams import Streams
from dominion_theory.planet import biome_names

SMALL = {
    'planet.circumference_km': 4000,
    'planet.window.width': 32,
    'planet.window.height': 16,
    'encounters.chance': 0.0,
    'units.band.decisions.horizon': 0,
    'units.band.unease.gain': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
}
WEST = 100
NORTH = 50
ROWS = (('grass', 'grass', 'forest', 'forest', 'forest', 'forest'),) * 3
HOME = (WEST, NORTH + 1)
STRIPPED = [(x, y) for x in (WEST, WEST + 1) for y in range(NORTH, NORTH + 3)]
AFTERNOON = 100 + 2
GRASS = Ground('grass', 0.6, 0.4, 0.2, 1.0, False, False, 0)
FOREST = Ground('forest', 0.8, 0.5, 0.4, 0.5, True, False, 4)
UNKNOWN = Ground(None, 0.5, 0.5, 0.4, 0.7, False, True, 6)
STAY = Option(1, {'kind': 'stay-and-gather'}, 'proposal-stay-and-gather', 8, True, 0.5, GRASS)
EAST = Option(2, {'kind': 'go', 'to': {'x': 3, 'y': 0}}, 'proposal-go-forest', 5, False, 0.45, FOREST)
FAR = Option(3, {'kind': 'go', 'to': {'x': 9, 'y': 0}}, 'proposal-go-unknown', 1, False, 0.2, UNKNOWN)
CAMP = Option(4, {'kind': 'winter-camp'}, 'proposal-winter-camp', 0, False, 0.1, GRASS)
ABSTAINING = Option(5, {'kind': 'abstain'}, 'proposal-abstain', 0, False, 0.0, None)


@pytest.fixture
def params() -> Params:
    return load_params(overrides=SMALL)


def land(params: Params) -> Game:
    """
    A game with a player in the seat on a hand-made window on a summer afternoon, the land of the band stripped.
    """
    names = biome_names(params)
    biomes = np.array([[names.index(name) for name in row] for row in ROWS], dtype=np.uint8)
    rivers = np.zeros(biomes.shape, dtype=np.bool_)
    game = Game(7, params, Streams(7), Window(0, WEST, NORTH, len(ROWS[0]), len(ROWS)), biomes, rivers, seated=True)
    game.clock.parts = AFTERNOON
    for cell in STRIPPED:
        for prop in ('food', 'water'):
            game.cells.lower(cell, prop, 0.9)
    game.band = bands.start(game, *HOME, game.day, game.streams['people'])
    game.band.members = bands.adults(game.band.population)
    game.band.lore['known'] = list(params.skills)
    game.band.changed()
    return game


def seen(*options: Option, **fields: Any) -> Observation:
    given: dict[str, Any] = {
        'year': 1,
        'month': 4,
        'day': 1,
        'part': 'evening',
        'season': 'summer',
        'people': {'child': 0, 'adult': 15, 'elder': 0},
        'pregnant': 0,
        'injured': 0,
        'sick': 0,
        'states': (),
        'fatigue': 0.0,
        'food_days': 0.5,
        'water_days': 3.0,
        'hunger': 0.5,
        'thirst': 0.0,
        'skills': (),
        'goods': {},
        'kits': {},
        'status': 50.0,
        'voice': 3.0,
        'occasion': 'first',
        'sight': 2,
        'winter_left': 0.4,
        'options': options or (STAY, EAST, FAR, CAMP, ABSTAINING),
    }
    return Observation(**{**given, **fields})


def test_the_seat_sees_every_option_of_the_table_numbered_with_abstaining_last(params: Params) -> None:
    game = land(params)

    before = observe(game)
    game.step()
    found = observe(game)

    assert before is None
    assert found is not None and game.council is not None
    table = game.council['table']
    assert [option.number for option in found.options] == list(range(1, len(table) + 2))
    assert [option.proposal for option in found.options] == [
        *(entry['proposal'] for entry in table),
        {'kind': 'abstain'},
    ]
    assert [option.score for option in found.options[:-1]] == [entry['score'] for entry in table]
    assert found.leader is not None and found.leader.proposal == game.council['leader']
    assert (found.occasion, found.voice, found.status) == ('first', game.council['voice'], game.status)
    assert found.options[-1].ground is None
    walks = [option.ground for option in found.options if option.kind == 'go']
    assert walks and all(ground is not None and ground.route and not ground.unknown for ground in walks)
    assert found.people == {'child': 0, 'adult': 15, 'elder': 0}


def test_every_feature_of_the_document_is_measured() -> None:
    assert tuple(MEASURES) == FEATURES


def test_the_features_of_a_known_table() -> None:
    table = seen()
    named = [dict(zip(FEATURES, features(table, option), strict=True)) for option in table.options]

    assert named[1] == {
        'go': 1.0,
        'stay': 0.0,
        'winter': 0.0,
        'abstain': 0.0,
        'votes': pytest.approx(5 / 14),
        'leader': 0.0,
        'score': 0.45,
        'hunger_food': pytest.approx(0.4),
        'thirst_water': 0.0,
        'calm_threat': pytest.approx(0.2),
        'river': 1.0,
        'unknown': 0.0,
        'distance': 2.0,
        'winter_short': 0.0,
        'short_stay': 0.0,
        'outvoted': 0.0,
    }
    assert (named[0]['leader'], named[0]['short_stay'], named[0]['distance']) == (1.0, 1.0, 0.0)
    assert (named[2]['unknown'], named[2]['outvoted']) == (1.0, 0.5)
    assert (named[3]['winter'], named[3]['winter_short']) == (1.0, 0.4)
    assert named[4]['abstain'] == 1.0 and sum(named[4].values()) == 1.0


def test_a_mind_scores_by_its_weights_and_a_tie_goes_to_the_order_of_the_table() -> None:
    weighed = Mind(features=('score', 'leader'), weights=(1.0, 0.1))
    walking = Mind(features=('go',), weights=(1.0,))

    assert scores(weighed, seen()) == pytest.approx([0.6, 0.45, 0.2, 0.1, 0.0])
    assert choose(weighed, seen()) == 1
    assert choose(walking, seen()) == 2
    assert choose(Mind(features=('abstain',), weights=(-1.0,)), seen()) == 1


@pytest.mark.parametrize(('day', 'left'), [(5, 1.0), (49, 1.0), (50, 1.0), (75, 0.5), (99, pytest.approx(1 / 50))])
def test_the_share_of_the_camp_seasons_left_is_whole_before_them_and_shrinks_in_them(
    params: Params, day: int, left: Any
) -> None:
    assert _winter_left(params, day) == left
