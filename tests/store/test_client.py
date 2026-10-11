from typing import Any

import fakeredis

from dominion_theory.store.client import connect


def test_an_empty_url_gives_the_fake() -> None:
    assert isinstance(connect(''), fakeredis.FakeValkey)


def test_a_url_gives_a_client_for_that_server() -> None:
    client: Any = connect('valkey://alpha.example.com:6379/2')

    assert not isinstance(client, fakeredis.FakeValkey)
    assert client.connection_pool.connection_kwargs['host'] == 'alpha.example.com'
    assert client.connection_pool.connection_kwargs['db'] == 2
