from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest
from fastapi.testclient import TestClient

from dominion_theory.api import PREFIX, create_app
from dominion_theory.core.settings import Settings
from dominion_theory.runner import Service
from dominion_theory.store import GameStore, ValkeyStore

# A band that needs nothing, sees nothing and meets nothing: it camps, so the frame is tested alone.
QUIET = {
    'units.band.sight': 0,
    'units.band.consumption_per_day.forage': 0.0,
    'units.band.consumption_per_day.water': 0.0,
    'units.band.people.birth.conceive_per_day': 0.0,
    'units.band.people.injury.per_day': 0.0,
    'units.band.people.age.per_year': 0.0,
    'units.band.people.stages.adult.dies.frailty': 0.0,
    'encounters.chance': 0.0,
}
SMALL = {'planet.circumference_km': 4000, 'planet.window.width': 32, 'planet.window.height': 16, **QUIET}


@pytest.fixture
def store() -> GameStore:
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    return ValkeyStore(raw, timedelta(hours=2))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, tick_ms=2, updates_kept=4)


@pytest.fixture
def service(store: GameStore, settings: Settings) -> Service:
    return Service(store, settings)


@pytest.fixture
def client(settings: Settings, service: Service) -> Iterator[TestClient]:
    with TestClient(create_app(settings, service)) as opened:
        yield opened


@pytest.fixture
def new_game(client: TestClient) -> Callable[..., dict[str, Any]]:
    def create(**asked: Any) -> dict[str, Any]:
        answer = client.post(f'{PREFIX}/games', json={'overrides': SMALL, 'mode': 'step', 'seated': False, **asked})
        assert answer.status_code == 201
        created: dict[str, Any] = answer.json()
        return created

    return create
