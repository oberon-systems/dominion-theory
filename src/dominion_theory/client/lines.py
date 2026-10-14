"""
An update as a line of text: the date of the game, the band as it stands, the status, the words of the events.
"""

from collections.abc import Mapping
from typing import Any

from ..i18n import DATE, render

# The vocabulary of the API, as docs/api/commands.md and docs/api/protocol.md state it.
DIRECTIONS = ('north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west')
ACTIONS = ('move', 'gather', 'camp')
STATE = 'state-'
PEOPLE = 'line-people'
STORE = 'line-store'
STATUS = 'line-status'
COUNCIL = 'line-council'
VOTES = 'line-votes'
PROPOSAL = 'proposal-'
ACTION = 'line-action-'
DIRECTION = 'line-direction-'
MESSAGES: tuple[str, ...] = (
    PEOPLE,
    STORE,
    STATUS,
    COUNCIL,
    VOTES,
    *(f'{ACTION}{kind}' for kind in ACTIONS),
    *(f'{DIRECTION}{towards}' for towards in DIRECTIONS),
)

type Unit = Mapping[str, Any]


def words(message: Mapping[str, Any], lang: str) -> str:
    return render(message['key'], message.get('values'), lang)


def band_words(band: Unit, lang: str) -> str:
    action = band['action']
    told = {name: value for name, value in action.items() if name != 'kind'}
    parts = [render(PEOPLE, {'count': band['population']}, lang)]
    parts += [render(STORE, {'resource': name, 'amount': amount}, lang) for name, amount in band['stores'].items()]
    parts += [render(f'{STATE}{state}', lang=lang) for state in band['states']]
    parts.append(render(f'{ACTION}{action["kind"]}', told, lang))
    return ', '.join(parts) + '.'


def council_words(council: Mapping[str, Any], lang: str) -> str:
    """
    The table of the council of the day: every option the others voted for, with its votes.
    """
    told = []
    for entry in council['table']:
        proposal = entry['proposal']
        name = f'{PROPOSAL}{proposal["kind"]}' + (f'-{proposal["towards"]}' if 'towards' in proposal else '')
        told.append(render(VOTES, {'proposal': name, 'votes': entry['votes']}, lang))
    return render(COUNCIL, {'table': '; '.join(told)}, lang)


def follow(band: Unit | None, update: Mapping[str, Any]) -> Unit | None:
    """
    The band after an update, from the one before it.
    """
    changes = update.get('changes', {})
    for unit in changes.get('units', []):
        band = unit
    if band is not None and band['id'] in changes.get('gone', []):
        return None
    return band


def line(update: Mapping[str, Any], lang: str, band: Unit | None = None) -> str:
    """
    The band is the one after the update, and the status is told only when the update moved it.
    """
    date = render(DATE, update['date'], lang)
    told = [] if band is None else [band_words(band, lang)]
    seat = update.get('changes', {}).get('seat', {})
    if seat.get('status') is not None:
        told.append(render(STATUS, {'status': seat['status']}, lang))
    told += [words(event, lang) for event in update['events']]
    if seat.get('council') and seat['council']['table']:
        told.append(council_words(seat['council'], lang))
    return f'{date}: {" ".join(told)}' if told else date
