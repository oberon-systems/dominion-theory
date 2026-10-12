import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlmodel import Session, select

from dominion_theory.core.errors import DominionError
from dominion_theory.db import (
    LOCAL_PROFILE,
    Database,
    Game,
    Profile,
    add_game,
    add_profile,
    change_profile,
    find_profile,
    local_profile,
    remove_profile,
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    database = Database(f'sqlite:///{tmp_path}/alpha.db')
    database.upgrade()
    with database.session() as opened:
        yield opened


def game(game_id: str, profile_id: str) -> Game:
    path = f'records/{game_id}.jsonl.gz'
    return Game(id=game_id, profile_id=profile_id, seed=42, params_hash='b41f', record_path=path)


def test_the_local_profile_is_created_once(session: Session) -> None:
    first = local_profile(session)
    second = local_profile(session)

    assert first.id == second.id == LOCAL_PROFILE
    assert first.locale == 'en'
    assert first.created_at == second.created_at
    assert len(session.exec(select(Profile)).all()) == 1


@pytest.mark.parametrize('locale', ['de', 'EN', ''])
def test_an_unknown_locale_is_refused(session: Session, locale: str) -> None:
    with pytest.raises(DominionError) as refused:
        add_profile(session, 'alpha', 'Alpha', locale)

    assert refused.value.message() == {'key': 'error-locale-unknown', 'values': {'locale': locale}}
    assert session.exec(select(Profile)).all() == []


def test_a_profile_changes_its_name_and_language(session: Session) -> None:
    add_profile(session, 'alpha', 'Alpha')

    change_profile(session, 'alpha', locale='ru')
    change_profile(session, 'alpha', name='Beta')

    found = find_profile(session, 'alpha')
    assert (found.name, found.locale) == ('Beta', 'ru')


def test_a_change_to_an_unknown_locale_is_refused(session: Session) -> None:
    add_profile(session, 'alpha', 'Alpha')

    with pytest.raises(DominionError):
        change_profile(session, 'alpha', locale='de')

    session.rollback()
    assert find_profile(session, 'alpha').locale == 'en'


def test_an_unknown_profile_is_not_found(session: Session) -> None:
    with pytest.raises(DominionError) as refused:
        find_profile(session, 'alpha')

    assert refused.value.message() == {'key': 'error-profile-not-found', 'values': {'id': 'alpha'}}


def test_a_game_is_kept_with_its_defaults(session: Session) -> None:
    add_profile(session, 'alpha', 'Alpha')

    add_game(session, game('7f3a9c1e', 'alpha'))

    found = session.get(Game, '7f3a9c1e')
    assert found is not None
    assert (found.seed, found.last_tick, found.preset, found.outcome, found.finished_at) == (42, 0, None, None, None)
    assert isinstance(found.started_at, int)
    assert abs(found.started_at - int(time.time())) < 60


def test_a_game_of_no_profile_is_refused(session: Session) -> None:
    with pytest.raises(DominionError) as refused:
        add_game(session, game('7f3a9c1e', 'alpha'))

    assert refused.value.key == 'error-profile-not-found'
    assert session.exec(select(Game)).all() == []


def test_removing_a_profile_leaves_no_game_of_it(session: Session) -> None:
    add_profile(session, 'alpha', 'Alpha')
    add_profile(session, 'beta', 'Beta')
    add_game(session, game('7f3a9c1e', 'alpha'))
    add_game(session, game('b02d4417', 'alpha'))
    add_game(session, game('c13e5528', 'beta'))

    remove_profile(session, 'alpha')

    assert [profile.id for profile in session.exec(select(Profile)).all()] == ['beta']
    assert [kept.id for kept in session.exec(select(Game)).all()] == ['c13e5528']
