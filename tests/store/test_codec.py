from typing import Any

import numpy as np

from dominion_theory.store.codec import pack, unpack


def test_a_snapshot_packs_and_unpacks_equal() -> None:
    snapshot: dict[str, Any] = {
        'tick': 7,
        'window': {'width': 3, 'height': 2},
        'seen': ['alpha', 'beta'],
        'grids': {
            'biomes': np.arange(6, dtype=np.uint8).reshape(2, 3),
            'water': np.linspace(0, 1, 12, dtype=np.float32).reshape(3, 4),
        },
    }

    held = unpack(pack(snapshot))

    assert {name: value for name, value in held.items() if name != 'grids'} == {
        name: value for name, value in snapshot.items() if name != 'grids'
    }
    assert list(held['grids']) == ['biomes', 'water']
    for name, grid in snapshot['grids'].items():
        assert held['grids'][name].dtype == grid.dtype
        assert np.array_equal(held['grids'][name], grid)


def test_a_view_is_packed_as_what_it_shows() -> None:
    grid = np.arange(12, dtype=np.int16).reshape(3, 4)[:, ::2]

    held = unpack(pack({'grids': {'alpha': grid}}))

    assert np.array_equal(held['grids']['alpha'], grid)


def test_an_unpacked_grid_can_be_written() -> None:
    held = unpack(pack({'grids': {'alpha': np.zeros((2, 2), dtype=np.uint8)}}))

    held['grids']['alpha'][0, 0] = 1

    assert held['grids']['alpha'].sum() == 1


def test_grids_are_compressed() -> None:
    packed = pack({'grids': {'alpha': np.zeros((256, 256), dtype=np.uint8)}})

    assert len(packed) < 256 * 256 // 10


def test_a_snapshot_without_grids_gets_none() -> None:
    assert unpack(pack({'tick': 1})) == {'tick': 1, 'grids': {}}
