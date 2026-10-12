"""
The form of a command, as docs/api/commands.md states it. The rules are the engine's, not checked here.
"""

from collections.abc import Callable, Mapping
from typing import Any

from ..core.errors import DominionError
from ..engine import Command
from ..engine.commands import CALL_COUNCIL, PASS
from .errors import COMMAND_INVALID

DIRECTIONS = ('north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west')
MOVE = 'move'
PROPOSALS: dict[str, frozenset[str]] = {
    MOVE: frozenset({'kind', 'towards'}),
    'rest': frozenset({'kind'}),
    'stay-and-gather': frozenset({'kind'}),
}


def _nothing(fields: Mapping[str, Any]) -> bool:
    return not fields


def _council(fields: Mapping[str, Any]) -> bool:
    proposal = fields.get('proposal')
    if set(fields) != {'proposal'} or not isinstance(proposal, Mapping):
        return False
    kind = proposal.get('kind')
    if not isinstance(kind, str) or PROPOSALS.get(kind) != frozenset(proposal):
        return False
    return kind != MOVE or proposal['towards'] in DIRECTIONS


FORMS: dict[str, Callable[[Mapping[str, Any]], bool]] = {PASS: _nothing, CALL_COUNCIL: _council}


def read_command(seat: str, envelope: Mapping[str, Any]) -> Command:
    name, kind = envelope.get('id'), envelope.get('kind')
    if not isinstance(name, str) or not name or not isinstance(kind, str) or kind not in FORMS:
        raise DominionError(COMMAND_INVALID)
    command = Command.read(seat, envelope)
    if not FORMS[kind](command.fields):
        raise DominionError(COMMAND_INVALID)
    return command
