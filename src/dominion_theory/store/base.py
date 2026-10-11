"""
The game store as the runner sees it: five operations and the data they carry.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Meta:
    """
    What is known of a stored game without reading its snapshot.
    """

    seed: int
    params: str
    tick: int
    mode: str


@dataclass(frozen=True)
class Stored:
    meta: Meta
    snapshot: dict[str, Any]
    changes: list[dict[str, Any]]


class GameStore(Protocol):
    def save_snapshot(self, game_id: str, snapshot: dict[str, Any], meta: Meta) -> None: ...

    def append_changes(self, game_id: str, tick: int, changes: dict[str, Any]) -> None: ...

    def load(self, game_id: str) -> Stored | None: ...

    def live_games(self) -> list[str]: ...

    def drop(self, game_id: str) -> None: ...
