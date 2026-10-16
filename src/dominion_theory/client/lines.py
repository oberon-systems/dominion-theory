"""
An update as a line of text: the date of the game, the band as it stands, the status, the words of the events.
The same line in parts, each with how it looks, and the options a player may name at a council.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, NamedTuple

from ..i18n import DATE, render

# The vocabulary of the API, as docs/api/commands.md and docs/api/protocol.md state it.
DIRECTIONS = ('north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west')
ACTIONS = ('move', 'roam', 'gather', 'camp')
STAGES = ('child', 'adult', 'elder')
STATE = 'state-'
PEOPLE = 'line-people'
STAGE = 'line-stage-'
CONDITIONS = ('pregnant', 'injured')
CONDITION = 'line-'
STORE = 'line-store'
STATUS = 'line-status'
COUNCIL = 'line-council'
VOTES = 'line-votes'
PROPOSAL = 'proposal-'
ACTION = 'line-action-'
DIRECTION = 'line-direction-'
QUESTION = 'play-question'
LEADER = 'play-leader'
ABSTAIN = 'play-abstain'
ANSWER = 'play-answer'
AWAY = 'play-away'
UNCLEAR = 'play-unclear'
FATIGUE = 'play-fatigue'
INTENT = 'play-intent'
RIVER = 'play-river'
GONE = 'play-gone'
OVER = 'play-over'
ENDS = ('banished', 'died')
EVENING = 'play-evening'
NEXT = 'play-next'
AGREED = 'council-agreed'
UNKNOWN = 'play-unknown'
PROPERTY = 'play-property-'
PROPERTIES = ('water', 'food', 'threat', 'passability')
TITLE = 'play-title-'
PANES = ('band', 'cell', 'log', 'council')
MESSAGES: tuple[str, ...] = (
    PEOPLE,
    STORE,
    STATUS,
    COUNCIL,
    VOTES,
    QUESTION,
    LEADER,
    ABSTAIN,
    ANSWER,
    AWAY,
    UNCLEAR,
    FATIGUE,
    INTENT,
    RIVER,
    GONE,
    OVER,
    *(f'{OVER}-{end}' for end in ENDS),
    EVENING,
    NEXT,
    UNKNOWN,
    *(f'{PROPERTY}{name}' for name in PROPERTIES),
    *(f'{TITLE}{pane}' for pane in PANES),
    *(f'{ACTION}{kind}' for kind in ACTIONS),
    *(f'{STAGE}{name}' for name in STAGES),
    *(f'{CONDITION}{name}' for name in CONDITIONS),
    *(f'{DIRECTION}{towards}' for towards in DIRECTIONS),
)

GO = 'go'
# Every proposal the menu lists after the voted ones.
PROPOSALS: tuple[dict[str, Any], ...] = ({'kind': 'stay-and-gather'},)
LOSSES = frozenset(
    {
        'command-refused',
        'band-state-began',
        'people-lost',
        'band-died',
        'encounter',
        'council-outvoted',
        'council-abstained',
        'proposal-failed',
        'proposal-disaster',
        'seat-blamed',
        'seat-banished',
    }
)
COUNCILS = ('council-', 'proposal-', 'intent-')

type Unit = Mapping[str, Any]


class Look(StrEnum):
    PLAIN = 'plain'
    DATE = 'date'
    BAND = 'band'
    STATE = 'state'
    STATUS = 'status'
    EVENT = 'event'
    COUNCIL = 'council'
    LOSS = 'loss'


class Part(NamedTuple):
    look: Look
    text: str


class Option(NamedTuple):
    proposal: Mapping[str, Any]
    votes: int
    leader: bool
    key: str
    far: int | None = None


def words(message: Mapping[str, Any], lang: str) -> str:
    return render(message['key'], message.get('values'), lang)


def _joined(pieces: list[Part], between: str) -> list[Part]:
    joined: list[Part] = []
    for piece in pieces:
        if joined:
            joined.append(Part(Look.PLAIN, between))
        joined.append(piece)
    return joined


def band_parts(band: Unit, lang: str) -> list[Part]:
    action = band['action']
    told = {name: value for name, value in action.items() if name != 'kind'}
    pieces = [Part(Look.BAND, render(PEOPLE, {'count': band['population']}, lang))]
    ages = {name: count for name, count in band.get('ages', {}).items() if count}
    # A band of one stage says no more than its people.
    if len(ages) > 1:
        pieces += [Part(Look.BAND, render(f'{STAGE}{name}', {'count': count}, lang)) for name, count in ages.items()]
    pieces += [
        Part(Look.STATE, render(f'{CONDITION}{name}', {'count': band[name]}, lang))
        for name in CONDITIONS
        if band.get(name)
    ]
    pieces += [
        Part(Look.BAND, render(STORE, {'resource': name, 'amount': amount}, lang))
        for name, amount in band['stores'].items()
    ]
    pieces += [Part(Look.STATE, render(f'{STATE}{state}', lang=lang)) for state in band['states']]
    pieces.append(Part(Look.BAND, render(f'{ACTION}{action["kind"]}', told, lang)))
    return [*_joined(pieces, ', '), Part(Look.PLAIN, '.')]


def band_words(band: Unit, lang: str) -> str:
    return ''.join(part.text for part in band_parts(band, lang))


def proposal_key(proposal: Mapping[str, Any]) -> str:
    """
    The words of a proposal with no place to tell its way from.
    """
    return f'{PROPOSAL}{proposal["kind"]}'


def council_words(council: Mapping[str, Any], lang: str) -> str:
    """
    The table of the council of the day: every option the others voted for, with its votes.
    """
    told = [render(VOTES, {'proposal': entry['key'], 'votes': entry['votes']}, lang) for entry in council['table']]
    return render(COUNCIL, {'table': '; '.join(told)}, lang)


def options(council: Mapping[str, Any], place: tuple[int, int] | None = None) -> list[Option]:
    """
    Every proposal the player may name: the table's in its order, a go with the cells to its target from the
    place given, then those with no votes in the fixed order.
    """
    leader = council.get('leader')
    listed = [
        Option(entry['proposal'], entry['votes'], entry['proposal'] == leader, entry['key'], _far(entry, place))
        for entry in council['table']
    ]
    voted = [option.proposal for option in listed]
    listed += [Option(proposal, 0, False, proposal_key(proposal)) for proposal in PROPOSALS if proposal not in voted]
    return listed


def _far(entry: Mapping[str, Any], place: tuple[int, int] | None) -> int | None:
    proposal = entry['proposal']
    if place is None or proposal['kind'] != GO:
        return None
    return int(max(abs(proposal['to']['x'] - place[0]), abs(proposal['to']['y'] - place[1])))


def look(key: str) -> Look:
    if key in LOSSES:
        return Look.LOSS
    if key.startswith(COUNCILS):
        return Look.COUNCIL
    return Look.EVENT


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


def parts(update: Mapping[str, Any], lang: str, band: Unit | None = None) -> list[Part]:
    """
    The line of an update in pieces, each with how it looks; their texts together are the line.
    """
    date = Part(Look.DATE, render(DATE, update['date'], lang))
    told: list[list[Part]] = [] if band is None else [band_parts(band, lang)]
    seat = update.get('changes', {}).get('seat', {})
    if seat.get('status') is not None:
        told.append([Part(Look.STATUS, render(STATUS, {'status': seat['status']}, lang))])
    told += [[Part(look(event['key']), words(event, lang))] for event in update['events']]
    if seat.get('council') and seat['council']['table']:
        told.append([Part(Look.COUNCIL, council_words(seat['council'], lang))])
    if not told:
        return [date]
    said: list[Part] = [date, Part(Look.PLAIN, ': '), *told[0]]
    for group in told[1:]:
        said += [Part(Look.PLAIN, ' '), *group]
    return said


def line(update: Mapping[str, Any], lang: str, band: Unit | None = None) -> str:
    """
    The band is the one after the update, and the status is told only when the update moved it.
    """
    return ''.join(part.text for part in parts(update, lang, band))
