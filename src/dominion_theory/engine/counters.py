"""
Counters: one number about the whole game at one tick, declared by the rules that keep it.
"""

from collections.abc import Callable


class Counters:
    """
    A row of values in the order of declaration, which a new counter never changes.
    """

    def __init__(self) -> None:
        self._readers: dict[str, Callable[[], float]] = {}

    def declare(self, name: str, read: Callable[[], float]) -> None:
        if name in self._readers:
            raise ValueError(f'the counter {name} is declared twice')
        self._readers[name] = read

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._readers)

    def row(self) -> list[float]:
        return [read() for read in self._readers.values()]
