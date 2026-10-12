import socket
import threading
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import fakeredis
import pytest
import uvicorn

from dominion_theory.api import create_app
from dominion_theory.client import Api
from dominion_theory.core.settings import Settings
from dominion_theory.runner import Service
from dominion_theory.store import ValkeyStore

STARTS_WITHIN = 10.0


@pytest.fixture
def server(tmp_path: Path) -> Iterator[str]:
    """
    The application behind a real socket of the loopback address, in a thread of the test's process.
    """
    settings = Settings(data_dir=tmp_path, tick_ms=2)
    raw: Any = fakeredis.FakeValkey(server=fakeredis.FakeServer(server_type='valkey'))
    app = create_app(settings, Service(ValkeyStore(raw, timedelta(hours=2)), settings))
    running = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=0, log_level='warning'))
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + STARTS_WITHIN
    while not running.started:
        assert thread.is_alive() and time.monotonic() < deadline
        time.sleep(0.01)
    port = running.servers[0].sockets[0].getsockname()[1]
    yield f'http://127.0.0.1:{port}'
    running.should_exit = True
    thread.join()


@pytest.fixture
def api(server: str) -> Iterator[Api]:
    opened = Api(server)
    yield opened
    opened.close()


@pytest.fixture
def unused_address() -> str:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return f'http://127.0.0.1:{probe.getsockname()[1]}'
