"""
Profiles: the local one, changing one, and removing one with everything that refers to it.
"""

from sqlmodel import Session, delete

from ..core.errors import DominionError
from .models import METADATA, Profile

LOCALES = ('en', 'ru')
LOCAL_PROFILE = 'local'
LOCALE_UNKNOWN = 'error-locale-unknown'
PROFILE_NOT_FOUND = 'error-profile-not-found'

# Every table and column that refers to a profile. A test fails when one is missing.
PROFILE_COLUMNS: tuple[tuple[str, str], ...] = (('games', 'profile_id'),)


def check_locale(locale: str) -> str:
    if locale not in LOCALES:
        raise DominionError(LOCALE_UNKNOWN, locale=locale)
    return locale


def add_profile(session: Session, profile_id: str, name: str, locale: str = 'en') -> Profile:
    profile = Profile(id=profile_id, name=name, locale=check_locale(locale))
    session.add(profile)
    session.commit()
    return profile


def find_profile(session: Session, profile_id: str) -> Profile:
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise DominionError(PROFILE_NOT_FOUND, id=profile_id)
    return profile


def change_profile(session: Session, profile_id: str, name: str | None = None, locale: str | None = None) -> Profile:
    profile = find_profile(session, profile_id)
    if name is not None:
        profile.name = name
    if locale is not None:
        profile.locale = check_locale(locale)
    session.add(profile)
    session.commit()
    return profile


def local_profile(session: Session) -> Profile:
    return session.get(Profile, LOCAL_PROFILE) or add_profile(session, LOCAL_PROFILE, LOCAL_PROFILE)


def remove_profile(session: Session, profile_id: str) -> None:
    # Parent first: a dependent row committed meanwhile is then still seen and removed.
    profiles = METADATA.tables['profiles']
    session.exec(delete(profiles).where(profiles.c.id == profile_id))
    for name, column in PROFILE_COLUMNS:
        table = METADATA.tables[name]
        session.exec(delete(table).where(table.c[column] == profile_id))
    session.commit()
