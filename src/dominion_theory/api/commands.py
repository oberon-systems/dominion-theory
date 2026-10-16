"""
The form of a command, as docs/api/commands.md states it. The rules are the engine's, not checked here.
"""

from collections.abc import Callable, Mapping
from typing import Any

from ..core.errors import DominionError
from ..engine import Command
from ..engine.commands import PASS, VOTE
from ..engine.council import answer
from .errors import COMMAND_INVALID


def _nothing(fields: Mapping[str, Any]) -> bool:
    return not fields


def _vote(fields: Mapping[str, Any]) -> bool:
    return answer(fields) is not None


FORMS: dict[str, Callable[[Mapping[str, Any]], bool]] = {PASS: _nothing, VOTE: _vote}


def read_command(seat: str, envelope: Mapping[str, Any]) -> Command:
    name, kind = envelope.get('id'), envelope.get('kind')
    if not isinstance(name, str) or not name or not isinstance(kind, str) or kind not in FORMS:
        raise DominionError(COMMAND_INVALID)
    command = Command.read(seat, envelope)
    if not FORMS[kind](command.fields):
        raise DominionError(COMMAND_INVALID)
    return command
