"""
Noise Base Settings
"""

from collections.abc import KeysView
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Noise:
    """
    Default Noise Settings Class
    """

    scale: int
    octaves: int
    persistence: float

    def keys(self) -> KeysView[str]:
        return self.__dataclass_fields__.keys()

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
