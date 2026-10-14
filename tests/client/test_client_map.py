from typing import Any

import click

from dominion_theory.client.drawing import Watched, pictured, rgb

COLOURS = {'forest': '#006400', 'grass': '#7cfc00'}
# Three cells by two from x 10 and y 20; the band stands on 11, 21 and knows three cells.
KNOWN: dict[str, Any] = {
    'scale': 0,
    'x': 10,
    'y': 20,
    'width': 3,
    'height': 2,
    'biomes': ['forest', 'grass'],
    'cells': [None, 0, 1, None, 0, None],
    'rivers': [None, 1, 0, None, 0, None],
    'food': [None, 0.5, 0.9, None, 0.4, None],
    'seen': [None, 3, 3, None, 3, None],
}
BAND = {
    'place': {'scale': 0, 'x': 11, 'y': 20},
    'reason': {'action': 'gather', 'resource': 'forage', 'need': 'hunger', 'score': 0.41891, 'pull': None},
}


def test_a_colour_is_read_as_red_green_and_blue() -> None:
    assert rgb('#006400') == (0, 100, 0)


def test_the_map_is_cut_to_the_known_cells_with_the_band_and_the_rivers() -> None:
    rows = list(pictured(KNOWN, COLOURS, (11, 21)))

    assert [click.unstyle(row) for row in rows] == ['♣~" ', '@   ']
    assert '\x1b[48;2;0;100;0m' in rows[0]


def test_a_band_that_knows_nothing_draws_no_map() -> None:
    assert not list(pictured({**KNOWN, 'cells': [None] * 6}, COLOURS, (11, 21)))


def test_the_band_cell_is_told_with_what_moved_in_the_update() -> None:
    watched = Watched()
    watched.learn(KNOWN)

    watched.take(
        {
            'known': [{'x': 11, 'y': 20, 'biome': 'forest', 'river': True, 'food': 0.45, 'seen': 4}],
            'cells': [{'x': 11, 'y': 20, 'water': 1.0, 'food': 0.7}],
        }
    )

    assert watched.said(BAND) == (
        '@ 11,20 | forest river | known food 0.45 (-0.05), seen 4 (+1) | stock water 1, food 0.7 '
        '| reason action gather, resource forage, need hunger, score 0.419'
    )


def test_a_change_is_told_only_in_the_update_that_made_it() -> None:
    watched = Watched()
    watched.take({'cells': [{'x': 11, 'y': 20, 'water': 1.0, 'food': 0.7}]})
    watched.take({'cells': [{'x': 11, 'y': 20, 'water': 1.0, 'food': 0.6}]})
    moved = watched.said(BAND)
    watched.take({})

    assert '| stock water 1, food 0.6 (-0.1) |' in moved
    assert '| stock water 1, food 0.6 |' in watched.said(BAND)
