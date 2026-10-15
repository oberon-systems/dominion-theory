import pytest

from dominion_theory.content import Params, load_params

SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16}
# The pull of the unknown and unease have tests of their own; the rest see the land the band knows.
PLAIN = {**SMALL, 'units.band.decisions.horizon': 0, 'units.band.unease.gain': 0.0}


@pytest.fixture
def params() -> Params:
    return load_params(overrides=PLAIN)
