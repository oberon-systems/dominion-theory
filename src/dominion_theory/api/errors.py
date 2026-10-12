"""
Errors of the API: a message key with values and a status of the table Errors of docs/api/protocol.md.
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..core.errors import DominionError
from ..db.profiles import PROFILE_NOT_FOUND
from ..i18n import LOCALE_UNKNOWN
from ..runner import CLOCK_RUNNING, GAME_ENDED, GAME_NOT_FOUND, RECORD_UNREADABLE

REQUEST_UNREADABLE = 'error-request-unreadable'
COMMAND_INVALID = 'error-command-invalid'
# Declared by content, which the api does not import.
PRESET_NOT_FOUND = 'error-preset-not-found'
PARAMS_INVALID = 'error-params-invalid'

UNREADABLE = 400
NOT_FOUND = 404
ENDED = 409
FAILED_CHECK = 422

STATUSES: dict[str, int] = {
    REQUEST_UNREADABLE: UNREADABLE,
    GAME_NOT_FOUND: NOT_FOUND,
    PRESET_NOT_FOUND: NOT_FOUND,
    LOCALE_UNKNOWN: NOT_FOUND,
    PROFILE_NOT_FOUND: NOT_FOUND,
    RECORD_UNREADABLE: NOT_FOUND,
    GAME_ENDED: ENDED,
    CLOCK_RUNNING: ENDED,
    PARAMS_INVALID: FAILED_CHECK,
    COMMAND_INVALID: FAILED_CHECK,
}


class ApiError(DominionError):
    """
    A key answered with another status than its own, such as a language refused in a profile.
    """

    def __init__(self, status: int, key: str, **values: object) -> None:
        super().__init__(key, **values)
        self.status = status


def status_of(error: DominionError) -> int:
    if isinstance(error, ApiError):
        return error.status
    return STATUSES.get(error.key, 500)


def body_of(error: DominionError) -> dict[str, object]:
    body: dict[str, object] = jsonable_encoder(error.message())
    return body


async def _refused(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, DominionError):
        raise error
    return JSONResponse(body_of(error), status_code=status_of(error))


async def _unreadable(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({'key': REQUEST_UNREADABLE, 'values': {}}, status_code=UNREADABLE)


def install(app: FastAPI) -> None:
    app.add_exception_handler(DominionError, _refused)
    app.add_exception_handler(RequestValidationError, _unreadable)
