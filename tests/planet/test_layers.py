import numpy as np
import pytest

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
    damp = planet.moisture.model_copy(update={'scale_km': 500, 'octaves': 2})
    twins = layers(7, planet.circumference_km, same, same, damp, planet.temperature)

    moved = layers(7, planet.circumference_km, planet.elevation, same, damp, planet.temperature)

    assert not np.array_equal(twins.elevation(x, y), twins.relief(x, y))
    assert not np.array_equal(twins.elevation(x, y), twins.moisture(x, y))
    assert np.array_equal(made.elevation(x, y), moved.elevation(x, y))


def test_ridges_and_basins_shape_land_and_leave_the_sea_and_the_shore_alone(params: Params) -> None:
    planet = params.planet
    made = layers(7, planet.circumference_km, planet.elevation, planet.relief, planet.moisture, planet.temperature)
    still = planet.elevation.model_copy(
        update={
            'ridges': planet.elevation.ridges.model_copy(update={'weight': 0.0}),
            'basins': planet.elevation.basins.model_copy(update={'depth': 0.0}),
        }
    )
    plain = layers(7, planet.circumference_km, still, planet.relief, planet.moisture, planet.temperature)
    x, y = np.meshgrid(np.arange(5.0, 4000.0, 50.0), np.arange(5.0, 2000.0, 50.0))
    base = made.elevation(x, y)
    sea = float(np.median(base))
    land = base > sea

    lifted = made.height(x, y, sea, 2.0, 1.0)
    shaped = made.height(x, y, sea, 0.0, 1.0)

    assert np.array_equal(plain.height(x, y, sea, 0.0, 1.0), base - sea)
    assert np.array_equal(lifted > 0, land)
    assert np.array_equal(lifted[~land], (base - sea)[~land])
    assert (lifted[land] >= (base - sea)[land]).all()
    assert (lifted[land] > (base - sea)[land]).any()
    assert np.array_equal(shaped > 0, land)
    assert (shaped <= lifted).all()
    assert (shaped[land] < lifted[land]).any()
    assert np.array_equal(shaped[~land], lifted[~land])


def test_land_rises_around_the_centre_of_a_continent_and_nowhere_else(params: Params) -> None:
    planet = params.planet
    around = planet.circumference_km
    lone = planet.elevation.continents.model_copy(update={'count': 1, 'radius_km': 500, 'weight': 5.0, 'edge': 6})
    one = planet.elevation.model_copy(update={'continents': lone})
    bare = planet.elevation.model_copy(update={'continents': lone.model_copy(update={'count': 0})})
    made = layers(7, around, one, planet.relief, planet.moisture, planet.temperature).elevation
    plain = layers(7, around, bare, planet.relief, planet.moisture, planet.temperature).elevation
    again = layers(7, around, one, planet.relief, planet.moisture, planet.temperature).elevation
    other = layers(8, around, one, planet.relief, planet.moisture, planet.temperature).elevation
    x, y = np.meshgrid(np.arange(5.0, 4000.0, 50.0), np.arange(5.0, 2000.0, 50.0))
    east = x - made.centres[0, 0]
    away = np.hypot(east - around * np.round(east / around), y - made.centres[0, 1])

    lifted = made(x, y) - plain(x, y)

    assert (len(made.centres), len(plain.centres)) == (1, 0)
    assert np.array_equal(made.centres, again.centres)
    assert not np.array_equal(made.centres, other.centres)
    assert (lifted >= 0).all()
    assert lifted[away < 300].min() > 2.5
    assert (away > 1800).any()
    assert lifted[away > 1800].max() < 0.05


def test_moisture_follows_the_belts_of_latitude_and_dries_inland(params: Params) -> None:
    planet = params.planet
    belts = [{'latitude': 0.0, 'wet': 1.0}, {'latitude': 0.5, 'wet': 0.0}, {'latitude': 1.0, 'wet': 0.5}]
    wet = planet.moisture.model_validate({**planet.moisture.model_dump(), 'belts': belts, 'belt': 2.0, 'inland': 3.0})
    made = layers(7, planet.circumference_km, planet.elevation, planet.relief, wet, planet.temperature)
    x = np.full(5, 123.0)
    y = np.array([1000.0, 750.0, 500.0, 0.0, 1500.0])
    shore = np.zeros(5)
    noise = made.moisture(x, y)

    low = np.zeros(5)
    assert (made.damp(x, y, shore, low) - noise).tolist() == pytest.approx([2.0, 0.0, -2.0, 0.0, -2.0])
    dried = made.damp(x, y, shore + wet.inland_km, low) - made.damp(x, y, shore, low)
    assert dried.tolist() == pytest.approx([-1.5] * 5)
    assert (made.damp(x, y, shore + np.inf, low) - made.damp(x, y, shore, low)).tolist() == pytest.approx([-3.0] * 5)


def test_heights_catch_moisture_and_belts_can_tell_north_from_south(params: Params) -> None:
    planet = params.planet
    belts = [{'latitude': -1.0, 'wet': 0.0}, {'latitude': 1.0, 'wet': 1.0}]
    given = {**planet.moisture.model_dump(), 'belts': belts, 'belt': 1.0, 'inland': 0.0, 'heights': 2.0}
    wet = planet.moisture.model_validate(given)
    made = layers(7, planet.circumference_km, planet.elevation, planet.relief, wet, planet.temperature)
    x = np.full(3, 123.0)
    y = np.array([0.0, 1000.0, 2000.0])
    none = np.zeros(3)
    noise = made.moisture(x, y)

    assert (made.damp(x, y, none, none) - noise).tolist() == pytest.approx([1.0, 0.0, -1.0])
    assert (made.damp(x, y, none, np.array([0.5, 1.0, -1.0])) - made.damp(x, y, none, none)).tolist() == [1.0, 2.0, 0.0]


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

    warmer = calm.model_copy(update={'warmth': 0.25})
    warm = layers(7, planet.circumference_km, planet.elevation, planet.relief, planet.moisture, warmer)
    assert warm.temperature(x, y, np.zeros(3)).tolist() == [0.25, 0.75, 1.0]
