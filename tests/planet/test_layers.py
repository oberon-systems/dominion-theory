import numpy as np

from dominion_theory.content import Params
from dominion_theory.planet import Planet
from dominion_theory.planet.layers import layers


def test_layers_stay_in_their_ranges(params: Params) -> None:
    world = Planet(7, params).read(0, 0, 400, 200, 10)

    assert -1.0 <= world.elevation.min() < 0.0 < world.elevation.max() <= 1.0
    for layer in (world.relief, world.moisture, world.temperature):
        assert layer.min() >= 0.0
        assert layer.max() <= 1.0
        assert layer.std() > 0.05


def test_every_layer_has_its_own_stream(params: Params) -> None:
    planet = params.planet
    made = layers(7, planet.circumference_km, planet.elevation, planet.relief, planet.moisture, planet.temperature)
    x, y = np.meshgrid(np.arange(5.0, 400.0, 10.0), np.arange(5.0, 400.0, 10.0))
    same = planet.elevation.model_copy(update={'scale_km': 500, 'octaves': 2})
    twins = layers(7, planet.circumference_km, same, same, same, planet.temperature)

    moved = layers(7, planet.circumference_km, planet.elevation, same, same, planet.temperature)

    assert not np.array_equal(twins.elevation(x, y), twins.relief(x, y))
    assert not np.array_equal(twins.elevation(x, y), twins.moisture(x, y))
    assert np.array_equal(made.elevation(x, y), moved.elevation(x, y))


def test_temperature_falls_to_the_poles_and_with_height(params: Params) -> None:
    planet = params.planet
    calm = planet.temperature.model_copy(update={'noise': 0.0})
    made = layers(7, planet.circumference_km, planet.elevation, planet.relief, planet.moisture, calm)
    x = np.zeros(3)
    y = np.array([0.0, 500.0, 1000.0])

    assert made.temperature(x, y, np.zeros(3)).tolist() == [0.0, 0.5, 1.0]
    assert made.temperature(x, y, np.ones(3)).tolist() == [0.0, 0.5 - calm.lapse, 1.0 - calm.lapse]
    assert made.temperature(x, y, -np.ones(3)).tolist() == [0.0, 0.5, 1.0]
    assert np.array_equal(made.temperature(x, 2000.0 - y, np.zeros(3)), made.temperature(x, y, np.zeros(3)))
