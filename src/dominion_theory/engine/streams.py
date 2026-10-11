"""
Random numbers of a game: one named stream per subsystem, each derived from the seed.
"""

from collections.abc import Mapping
from typing import Any

import numpy as np


class Streams:
    """
    A stream is made when first asked for, so a draw in one never shifts another.
    """

    def __init__(self, seed: int, states: Mapping[str, Any] | None = None) -> None:
        self.seed = seed
        self._streams: dict[str, np.random.Generator] = {}
        for name, state in (states or {}).items():
            self[name].bit_generator.state = state

    def __getitem__(self, name: str) -> np.random.Generator:
        if name not in self._streams:
            sequence = np.random.SeedSequence(self.seed, spawn_key=tuple(name.encode()))
            self._streams[name] = np.random.Generator(np.random.PCG64(sequence))
        return self._streams[name]

    def states(self) -> dict[str, Any]:
        return {name: dict(self._streams[name].bit_generator.state) for name in sorted(self._streams)}
