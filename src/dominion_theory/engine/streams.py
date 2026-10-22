"""
Random numbers of a game: one named stream per subsystem, each derived from the seed and the draw.
"""

from collections.abc import Mapping
from typing import Any

import numpy as np


class Streams:
    """
    A stream is made when first asked for, so a draw in one never shifts another. The draw picks another life
    on the same land: docs/lab/runs.md, A land and a draw; draw 0 is the game of the seed alone.
    """

    def __init__(self, seed: int, states: Mapping[str, Any] | None = None, draw: int = 0) -> None:
        self.seed = seed
        self.draw = draw
        self._streams: dict[str, np.random.Generator] = {}
        for name, state in (states or {}).items():
            self[name].bit_generator.state = state

    def __getitem__(self, name: str) -> np.random.Generator:
        if name not in self._streams:
            entropy = self.seed if self.draw == 0 else [self.seed, self.draw]
            sequence = np.random.SeedSequence(entropy, spawn_key=tuple(name.encode()))
            self._streams[name] = np.random.Generator(np.random.PCG64(sequence))
        return self._streams[name]

    def states(self) -> dict[str, Any]:
        return {name: dict(self._streams[name].bit_generator.state) for name in sorted(self._streams)}
