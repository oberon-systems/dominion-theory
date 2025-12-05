"""
Noise Base Settings
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Noise:
    """
    Default Noise Settings Class
    """
    scale: int
    octaves: int
    persistence: float
    seed: int

    def keys(self):
        # pylint: disable-next=no-member
        return self.__dataclass_fields__.keys()

    def __getitem__(self, key):
        return getattr(self, key)
