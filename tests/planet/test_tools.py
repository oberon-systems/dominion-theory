from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner

from dominion_theory.content import Params
from dominion_theory.planet import Region, biome_names
from dominion_theory.planet.tools import pictures
from dominion_theory.planet.tools.cli import cli

SMALL = ('planet.circumference_km=4000', 'planet.window.width=32', 'planet.window.height=16')


def region(params: Params, rows: list[list[str]], rivers: list[list[bool]]) -> Region:
    names = biome_names(params)
    codes = np.array([[names.index(name) for name in row] for row in rows], dtype=np.uint8)
    layer = np.zeros(codes.shape)
    return Region(layer, layer, layer, layer, layer, codes, np.array(rivers, dtype=np.bool_))


@pytest.fixture
def land(params: Params) -> Region:
    return region(params, [['forest', 'grass'], ['water', 'forest']], [[False, False], [False, True]])


def run(tmp_path: Path, name: str, *options: str) -> tuple[Path, str]:
    out = tmp_path / name
    given = [part for item in SMALL for part in ('--set', item)]
    result = CliRunner().invoke(cli, ['--seed', '5', *given, '--out', str(out), *options])

    assert result.exit_code == 0, result.output
    return out, result.output


def test_biomes_are_drawn_in_their_colours_with_rivers_over_them(params: Params, land: Region) -> None:
    picture = pictures.biomes(params, land)

    assert picture.shape == (2, 2, 3)
    assert tuple(picture[0, 0]) == pictures.rgb(params.biomes['forest'].colour)
    assert tuple(picture[0, 1]) == pictures.rgb(params.biomes['grass'].colour)
    assert tuple(picture[1, 0]) == pictures.rgb(params.biomes['water'].colour)
    assert tuple(picture[1, 1]) == pictures.rgb(pictures.RIVER)


def test_open_water_is_drawn_darker_the_deeper_it_lies_and_ice_is_not(params: Params) -> None:
    names = biome_names(params)
    codes = np.array([[names.index('water'), names.index('water'), names.index('ice')]], dtype=np.uint8)
    flat = np.zeros((1, 3))
    deep = Region(np.array([[-0.1, -1.0, -1.0]]), flat, flat, flat, flat, codes, np.zeros((1, 3), dtype=np.bool_))

    picture = pictures.biomes(params, deep)

    assert picture[0, 0].sum() > picture[0, 1].sum()
    assert picture[0, 0].sum() < sum(pictures.rgb(params.biomes['water'].colour))
    assert tuple(picture[0, 2]) == pictures.rgb(params.biomes['ice'].colour)


def test_a_property_is_the_base_with_the_river_and_the_season_laid_over(params: Params, land: Region) -> None:
    forest = params.biomes['forest'].eras['band'].properties
    effects = params.planet.rivers.effects['band']
    plain = pictures.values(params, 'band', 'food', land)
    winter = pictures.values(params, 'band', 'food', land, 'winter')
    walked = pictures.values(params, 'band', 'passability', land)

    assert plain[0, 0] == forest['food'].base
    assert plain[1, 1] == min(forest['food'].base + effects['food'].amount, 1.0)
    assert winter[0, 0] == pytest.approx(forest['food'].base * forest['food'].seasons['winter'].amount)
    assert walked[1, 1] == pytest.approx(forest['passability'].base * effects['passability'].amount)
    assert walked[1, 0] == 0.0


def test_values_are_shaded_from_dark_to_bright() -> None:
    picture = pictures.shaded(np.array([[0.0, 1.0]]))

    assert tuple(picture[0, 0]) == pictures.rgb(pictures.LOW)
    assert tuple(picture[0, 1]) == pictures.rgb(pictures.HIGH)


def test_pictures_are_tiled_two_in_a_row_framed_and_enlarged() -> None:
    one = np.full((4, 6, 3), 9, dtype=np.uint8)
    gap = pictures.PADDING

    assert pictures.tiled([one, one, one]).shape == (2 * 4 + 3 * gap, 2 * 6 + 3 * gap, 3)
    assert pictures.enlarged(one, 3).shape == (12, 18, 3)

    framed = pictures.framed(one, 1, 1, 3, 2)
    assert tuple(framed[1, 1]) == tuple(framed[2, 3]) == pictures.rgb(pictures.FRAME)
    assert tuple(framed[0, 0]) == tuple(framed[3, 3]) == (9, 9, 9)
    assert tuple(one[1, 1]) == (9, 9, 9)


def test_square_corners_of_a_shore_are_counted() -> None:
    square = np.zeros((40, 40), dtype=np.bool_)
    square[10:30, 10:30] = True
    rows, columns = np.indices((40, 40))
    round_lake = (rows - 20) ** 2 + (columns - 20) ** 2 < 12**2

    assert pictures.corners(square) == 4
    assert pictures.corners(round_lake) == 0
    assert pictures.corners(np.zeros((40, 40), dtype=np.bool_)) == 0
    assert pictures.corners(np.zeros((1, 40), dtype=np.bool_)) == 0


def test_shares_of_biomes_add_up_to_the_whole(params: Params, land: Region) -> None:
    found = pictures.shares(params, land)

    assert tuple(found) == biome_names(params)
    assert found['forest'] == 0.5
    assert found['grass'] == found['water'] == 0.25
    assert sum(found.values()) == 1.0


def test_the_window_is_written_to_a_file_the_same_for_the_same_seed(tmp_path: Path) -> None:
    first, output = run(tmp_path, 'alpha.png')
    second, _ = run(tmp_path, 'beta.png')

    assert 'default, seed 5: the window at' in output
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().startswith(b'\x89PNG')


def test_the_whole_planet_and_every_property_are_written(tmp_path: Path) -> None:
    planet, output = run(tmp_path, 'alpha.png', '--planet', '--cell-km', '100')
    properties, _ = run(tmp_path, 'beta.png', '--show', 'all', '--season', 'winter')

    assert 'water' in output
    assert planet.stat().st_size > 0
    assert properties.stat().st_size > 0


@pytest.mark.parametrize(
    'options',
    [
        ('--show', 'alpha'),
        ('--season', 'alpha'),
        ('--planet', '--cell-km', '300'),
        ('--set', 'alpha'),
        ('--preset', 'alpha'),
    ],
)
def test_an_option_that_makes_no_sense_is_refused(tmp_path: Path, options: tuple[str, ...]) -> None:
    given = [part for item in SMALL for part in ('--set', item)]
    result = CliRunner().invoke(cli, ['--seed', '5', *given, '--out', str(tmp_path / 'alpha.png'), *options])

    assert result.exit_code != 0
    assert not (tmp_path / 'alpha.png').exists()
