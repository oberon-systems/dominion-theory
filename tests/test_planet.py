import pytest

from dominion_theory.planet import atlas, settings
from dominion_theory.planet.settings.biomes.base import Biome


def test_atlas_fills_every_cell_with_a_biome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'width', 24)
    monkeypatch.setattr(settings, 'height', 16)

    world = atlas()

    assert world.shape == (16, 24)
    assert all(isinstance(cell, Biome) for cell in world.flat)
