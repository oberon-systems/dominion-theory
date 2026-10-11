from ..core.settings import Settings, get_settings
from .base import GameStore, Meta, Stored
from .client import connect
from .valkey_store import ValkeyStore


def open_store(settings: Settings | None = None) -> GameStore:
    settings = settings or get_settings()
    return ValkeyStore(connect(settings.store_url), settings.store_ttl)


__all__ = [
    'GameStore',
    'Meta',
    'Stored',
    'ValkeyStore',
    'open_store',
]
