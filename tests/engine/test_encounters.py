from typing import Any

import numpy as np
import pytest

from dominion_theory.content import Params, load_params
from dominion_theory.engine import Game, encounters
from dominion_theory.engine import band as bands
from dominion_theory.engine.band import Band, adults, camp, gathering, moving

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
LIKELY = {**SMALL, 'encounters.chance': 1.0}


class Dice:
    """
    A stream that gives the numbers it was handed: whether it happens, which kind, what share.
    """

    def __init__(self, *numbers: float) -> None:
        self.numbers = numbers

    def random(self, count: int) -> Any:
        assert count == len(self.numbers)
        return np.array(self.numbers)


def dice(*numbers: float) -> Any:
    return Dice(*numbers)


def fitting(params: Params, biome: str, river: bool, action: dict[str, Any]) -> list[str]:
    kinds = params.encounters.kinds
    return [name for name in sorted(kinds) if encounters.fits(kinds[name], biome, river, action)]


def test_a_kind_fits_its_biomes_its_actions_and_its_resources(params: Params) -> None:
    assert fitting(params, 'forest', False, camp()) == ['predator']
    assert fitting(params, 'forest', True, moving('east')) == ['drowning', 'predator']
    assert fitting(params, 'forest', True, camp()) == ['predator']
    assert fitting(params, 'mountain', False, moving('east')) == ['accident', 'predator']
    assert fitting(params, 'mountain', False, gathering({'forage': 1.0})) == ['predator']
    assert fitting(params, 'shallows', False, gathering({'water': 1.0})) == ['drowning', 'predator']
    assert fitting(params, 'swamp', False, gathering({'water': 1.0})) == ['poisoning', 'predator']
    assert fitting(params, 'swamp', False, gathering({'forage': 1.0})) == ['predator']


def test_the_chance_follows_the_threat_and_the_action(params: Params) -> None:
    def met(happens: float, threat: float, action: dict[str, Any]) -> bool:
        return encounters.strike(params, 'forest', False, threat, action, dice(happens, 0.0, 0.0)) is not None

    assert (met(0.0049, 0.5, camp()), met(0.005, 0.5, camp())) == (True, False)
    assert (met(0.0149, 0.5, moving('east')), met(0.015, 0.5, moving('east'))) == (True, False)
    assert (met(0.0199, 1.0, gathering({'forage': 1.0})), met(0.02, 1.0, gathering({'forage': 1.0}))) == (True, False)
    assert not met(0.0, 0.0, camp())


def test_the_kind_is_drawn_by_weight_among_those_that_fit(params: Params) -> None:
    def kind(which: float) -> str:
        met = encounters.strike(params, 'swamp', False, 1.0, gathering({'water': 1.0}), dice(0.0, which, 0.0))
        assert met is not None
        return met[0]

    assert [kind(which) for which in (0.0, 0.5, 0.58, 0.99)] == ['poisoning', 'poisoning', 'predator', 'predator']


@pytest.mark.parametrize('share', [0.0, 0.34, 0.99])
def test_the_shares_lost_and_injured_are_drawn_between_the_bounds(params: Params, share: float) -> None:
    met = encounters.strike(params, 'forest', False, 1.0, moving('east'), dice(0.0, 0.0, share))

    assert met is not None
    assert met[0] == 'predator'
    assert met[1:] == pytest.approx((0.1 * share, 0.1 * share))


def test_a_band_in_camp_loses_half_the_share_and_is_hurt_the_same(params: Params) -> None:
    sheltered = encounters.strike(params, 'forest', False, 1.0, camp(), dice(0.0, 0.0, 0.5))
    walking = encounters.strike(params, 'forest', False, 1.0, moving('east'), dice(0.0, 0.0, 0.5))

    assert sheltered is not None and walking is not None
    assert sheltered[1:] == pytest.approx((walking[1] * 0.5, walking[2]))


def test_a_drowning_always_takes_somebody(params: Params) -> None:
    met = encounters.strike(params, 'shallows', False, 1.0, gathering({'water': 1.0}), dice(0.0, 0.0, 0.0))
    band = Band(id=1, x=0, y=0, members=adults(15))

    assert met == ('drowning', 0.05, 0.0)
    assert bands.struck(params, band, met[1], met[2], {}, np.random.default_rng(7)) == (1, 0)
    assert (band.population, band.members[0].player) == (14, True)


def played(seed: int, overrides: dict[str, Any], ticks: int = 100) -> tuple[Game, list[tuple[str, dict[str, Any]]]]:
    game = Game.create(seed=seed, params=load_params(overrides=overrides))
    told = []
    for _ in range(ticks):
        told += [(event.key, event.values) for event in game.step().events if event.key in ('encounter', 'people-lost')]
    return game, told


def test_encounters_strike_a_band_in_the_game_and_are_counted() -> None:
    game, told = played(7, LIKELY)
    counted = dict(zip(game.counters.names, game.counters.row(), strict=True))
    struck = [values for key, values in told if key == 'encounter']
    lost = [values['count'] for key, values in told if key == 'people-lost' and values['cause'] == 'encounter']

    assert struck
    assert all(values['kind'].startswith('encounter-') for values in struck)
    assert counted['encounters'] == len(struck)
    assert sum(values['lost'] for values in struck) == sum(lost) <= counted['deaths']


def test_encounters_are_the_same_for_the_same_seed() -> None:
    first, second = played(7, LIKELY), played(7, LIKELY)

    assert first[1] == second[1]
    assert first[0].state_hash() == second[0].state_hash()


def test_no_chance_means_no_encounter_and_the_stream_is_drawn_all_the_same() -> None:
    quiet, told = played(7, {**SMALL, 'encounters.chance': 0.0}, 20)
    loud, _ = played(7, LIKELY, 20)

    assert [key for key, _ in told if key == 'encounter'] == []
    assert quiet.streams.states()['encounters'] == loud.streams.states()['encounters']


def test_a_shared_gathering_meets_what_any_of_its_resources_meets(params: Params) -> None:
    both = gathering({'forage': 0.6, 'water': 0.4})

    assert fitting(params, 'swamp', False, both) == ['poisoning', 'predator']
