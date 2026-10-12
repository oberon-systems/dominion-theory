"""
What is not a game: health, the profile, the catalogues, the presets and the schema of the stream.
"""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ...core.errors import DominionError
from ...db import LOCAL_PROFILE, change_profile, local_profile
from ...db import Profile as Stored
from ...i18n import LOCALE_UNKNOWN, catalogue
from ..context import Ctx
from ..errors import FAILED_CHECK, ApiError
from ..schemas import Health, Presets, Profile, ProfileChange, stream_schema

SCHEMA = '/updates.schema.json'

router = APIRouter()


def _shown(profile: Stored) -> Profile:
    return Profile(id=profile.id, name=profile.name, language=profile.locale)


@router.get('/health')
async def health() -> Health:
    return Health()


@router.get('/profile')
async def profile(context: Ctx) -> Profile:
    with context.database.session() as session:
        return _shown(local_profile(session))


@router.patch('/profile')
async def change(body: ProfileChange, context: Ctx) -> Profile:
    with context.database.session() as session:
        try:
            return _shown(change_profile(session, LOCAL_PROFILE, body.name, body.language))
        except DominionError as error:
            if error.key != LOCALE_UNKNOWN:
                raise
            raise ApiError(FAILED_CHECK, error.key, **error.values) from error


@router.get('/locales/{lang}', response_class=PlainTextResponse)
async def locale(lang: str) -> str:
    return catalogue(lang)


@router.get('/presets')
async def presets(context: Ctx) -> Presets:
    return Presets(presets=context.service.presets())


@router.get(SCHEMA)
async def schema() -> dict[str, Any]:
    return stream_schema()
