from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from dominion_theory.core.settings import Settings, get_settings

NAMES = ('DATA_DIR', 'STORE_URL', 'STORE_TTL', 'DATABASE_URL', 'RECORDS_DIR', 'TICK_MS', 'SPECTATOR')


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in NAMES:
        monkeypatch.delenv(f'DT_{name}', raising=False)
    get_settings.cache_clear()


def test_defaults_work_with_nothing_set() -> None:
    settings = Settings()

    assert settings.data_dir == Path('data')
    assert settings.store_url == ''
    assert settings.store_ttl == timedelta(days=7)
    assert settings.database_url == 'sqlite:///data/dominion-theory.db'
    assert settings.records_dir == Path('data/records')
    assert settings.tick_ms == 500
    assert settings.spectator is True


def test_paths_follow_the_data_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('DT_DATA_DIR', str(tmp_path))

    settings = Settings()

    assert settings.database_url == f'sqlite:///{tmp_path}/dominion-theory.db'
    assert settings.records_dir == tmp_path / 'records'


def test_environment_overrides_every_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DT_STORE_URL', 'valkey://alpha.example.com:6379/0')
    monkeypatch.setenv('DT_STORE_TTL', '12h')
    monkeypatch.setenv('DT_DATABASE_URL', 'postgresql://beta.example.com/alpha')
    monkeypatch.setenv('DT_RECORDS_DIR', 'runs')
    monkeypatch.setenv('DT_TICK_MS', '50')
    monkeypatch.setenv('DT_SPECTATOR', 'false')

    settings = Settings()

    assert settings.store_url == 'valkey://alpha.example.com:6379/0'
    assert settings.store_ttl == timedelta(hours=12)
    assert settings.database_url == 'postgresql://beta.example.com/alpha'
    assert settings.records_dir == Path('runs')
    assert settings.tick_ms == 50
    assert settings.spectator is False


def test_a_tick_cannot_be_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DT_TICK_MS', '0')

    with pytest.raises(ValidationError):
        Settings()


def test_settings_are_built_once(monkeypatch: pytest.MonkeyPatch) -> None:
    first = get_settings()
    monkeypatch.setenv('DT_TICK_MS', '50')

    assert get_settings() is first
