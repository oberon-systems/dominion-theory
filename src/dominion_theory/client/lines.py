"""
An update as a line of text: the date of the game, the band as it stands, the status, the words of the events.
The same line in parts, each with how it looks, and the options a player may name at a council.
"""

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any, NamedTuple

from ..i18n import DATE, render
from .drawing import GLYPHS

# The vocabulary of the API, as docs/api/commands.md and docs/api/protocol.md state it.
DIRECTIONS = ('north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west')
ACTIONS = ('move', 'roam', 'gather', 'camp', 'build')
STAGES = ('child', 'adult', 'elder')
STATE = 'state-'
PEOPLE = 'line-people'
STAGE = 'line-stage-'
CONDITIONS = ('pregnant', 'injured')
CONDITION = 'line-'
BADLY = 'line-injured-badly'
WOUNDS = 'wounds'
HEAVY = 'heavy'
STORE = 'line-store'
CAMP = 'line-camp'
GATHERED = 'line-gathered'
SHARED = 'line-gathered-share'
AND = 'line-and'
ROLE = 'line-role-'
# The roles told by their count: everyone else gathers.
ROLES = ('nanny',)
SKILLS = 'line-skills'
SKILL = 'skill-'
STATUS = 'line-status'
COUNCIL = 'line-council'
VOTES = 'line-votes'
PROPOSAL = 'proposal-'
ACTION = 'line-action-'
DIRECTION = 'line-direction-'
QUESTION = 'play-question'
ANSWER = 'play-answer'
POINT = 'play-point'
KIND = 'play-kind-'
WHERE = 'play-where'
PICK = 'play-pick'
CURSOR = 'play-cursor'
PLACE = 'play-place'
LAND = 'place-'
THROUGH = 'place-through-'
STRANGE = 'place-unknown'
LEVELS = 3
QUALITIES = ('danger', 'river', 'rich', 'safe', 'plain')
DANGER = 0.4
RICH = 0.6
SAFE = 0.15
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
PANES = ('band', 'cell', 'target', 'log', 'council')
MESSAGES: tuple[str, ...] = (
    PEOPLE,
    BADLY,
    STORE,
    CAMP,
    GATHERED,
    SHARED,
    AND,
    *(f'{ROLE}{name}' for name in ROLES),
    SKILLS,
    STATUS,
    COUNCIL,
    VOTES,
    QUESTION,
    ANSWER,
    POINT,
    WHERE,
    PICK,
    CURSOR,
    PLACE,
    STRANGE,
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
    *(f'{KIND}{kind}' for kind in ('go', 'stay-and-gather', 'winter-camp', 'abstain')),
    *(f'{LAND}{biome}' for biome in GLYPHS),
    *(f'{THROUGH}{biome}' for biome in GLYPHS),
)

GO = 'go'
STAY = 'stay-and-gather'
WINTER = 'winter-camp'
ABSTAIN = 'abstain'
SILENCE = {'kind': ABSTAIN}
# The answers of the menu in its order; a go opens the places it may lead to.
KINDS = (GO, STAY, WINTER, ABSTAIN)
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
        'seat-blamed',
        'seat-banished',
    }
)
COUNCILS = ('council-', 'proposal-', 'intent-')

type Unit = Mapping[str, Any]
type Place = tuple[int, int]
type Known = Callable[[Place], Mapping[str, Any] | None]


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


class Way(NamedTuple):
    """
    Where a go leads as the band knows it: the biome of the target or None when unknown, whether it goes on
    through the land it stands on, how the target looks, and how far it lies.
    """

    land: str | None
    through: bool
    quality: str
    cells: int


class Option(NamedTuple):
    """
    An answer of the menu or a place of a go; the proposal is None for the go that opens the places.
    """

    kind: str
    proposal: Mapping[str, Any] | None
    leader: bool
    way: Way | None = None


class Menu(NamedTuple):
    """
    The answers, the places of the goes, the cell of the band and whether a place of the player's own may be named.
    """

    answers: list[Option]
    places: list[Option]
    place: Place | None
    pointing: bool = True


def words(message: Mapping[str, Any], lang: str) -> str:
    return render(message['key'], message.get('values'), lang)


def _joined(pieces: list[Part], between: str) -> list[Part]:
    joined: list[Part] = []
    for piece in pieces:
        if joined:
            joined.append(Part(Look.PLAIN, between))
        joined.append(piece)
    return joined


def doing(action: Mapping[str, Any], lang: str) -> str:
    """
    The words of an action; a gathering names its resources, most gathered first, with their shares when there
    are several.
    """
    told = {name: value for name, value in action.items() if name != 'kind'}
    if action['kind'] != 'gather':
        return render(f'{ACTION}{action["kind"]}', told, lang)
    shares = sorted(action['shares'].items(), key=lambda held: -held[1])
    key = GATHERED if len(shares) == 1 else SHARED
    names = [render(key, {'resource': name, 'percent': round(share * 100)}, lang) for name, share in shares]
    what = names[0] if len(names) == 1 else render(AND, {'first': ', '.join(names[:-1]), 'last': names[-1]}, lang)
    return render(f'{ACTION}gather', {'what': what}, lang)


def band_parts(band: Unit, lang: str) -> list[Part]:
    pieces = [Part(Look.BAND, render(PEOPLE, {'count': band['population']}, lang))]
    ages = {name: count for name, count in band.get('ages', {}).items() if count}
    # A band of one stage says no more than its people.
    if len(ages) > 1:
        pieces += [Part(Look.BAND, render(f'{STAGE}{name}', {'count': count}, lang)) for name, count in ages.items()]
    pieces += [Part(Look.STATE, _condition(band, name, lang)) for name in CONDITIONS if band.get(name)]
    roles = band.get('roles', {})
    pieces += [
        Part(Look.BAND, render(f'{ROLE}{name}', {'count': roles[name]}, lang)) for name in ROLES if roles.get(name)
    ]
    if _sheltered(band):
        pieces.append(Part(Look.BAND, render(CAMP, lang=lang)))
    if band.get('lore'):
        skills = ', '.join(render(f'{SKILL}{name}', lang=lang) for name in band['lore'])
        pieces.append(Part(Look.BAND, render(SKILLS, {'skills': skills}, lang)))
    pieces += [
        Part(Look.BAND, render(STORE, {'resource': name, 'amount': amount}, lang))
        for name, amount in band['stores'].items()
    ]
    pieces += [Part(Look.STATE, render(f'{STATE}{state}', lang=lang)) for state in band['states']]
    pieces.append(Part(Look.BAND, doing(band['action'], lang)))
    return [*_joined(pieces, ', '), Part(Look.PLAIN, '.')]


def _sheltered(band: Unit) -> bool:
    camp, place = band.get('camp'), band.get('place')
    if camp is None or place is None:
        return False
    return bool(camp['built'] >= 1 and (camp['x'], camp['y']) == (place['x'], place['y']))


def _condition(band: Unit, name: str, lang: str) -> str:
    badly = band.get(WOUNDS, {}).get(HEAVY, 0) if name == 'injured' else 0
    if badly:
        return render(BADLY, {'count': band[name], 'badly': badly}, lang)
    return render(f'{CONDITION}{name}', {'count': band[name]}, lang)


def band_words(band: Unit, lang: str) -> str:
    return ''.join(part.text for part in band_parts(band, lang))


def council_words(council: Mapping[str, Any], lang: str) -> str:
    """
    The table of the council of the day: every option the others voted for, with its votes.
    """
    told = [render(VOTES, {'proposal': entry['key'], 'votes': entry['votes']}, lang) for entry in council['table']]
    return render(COUNCIL, {'table': '; '.join(told)}, lang)


def target(proposal: Mapping[str, Any]) -> Place:
    return proposal['to']['x'], proposal['to']['y']


def quality(cell: Mapping[str, Any]) -> str:
    """
    How a known cell looks to the band, the first that holds of QUALITIES.
    """
    if cell.get('threat', 0.0) >= DANGER:
        return 'danger'
    if cell.get('river'):
        return 'river'
    if cell.get('food', 0.0) >= RICH:
        return 'rich'
    return 'safe' if cell.get('threat', 1.0) <= SAFE else 'plain'


def way(to: Place, place: Place, known: Known) -> Way:
    cells = max(abs(to[0] - place[0]), abs(to[1] - place[1]))
    cell, here = known(to), known(place)
    if cell is None:
        return Way(None, False, 'plain', cells)
    through = here is not None and here['biome'] == cell['biome']
    return Way(cell['biome'], through, quality(cell), cells)


def where(told: Way, lang: str) -> str:
    """
    The words of a place a go leads to: its land and whether it is near.
    """
    if told.land is None:
        land = render(STRANGE, lang=lang)
    elif told.through:
        land = render(f'{THROUGH}{told.land}', lang=lang)
    else:
        land = render(f'{LAND}{told.land}', {'quality': told.quality}, lang)
    return render(PLACE, {'land': land, 'cells': told.cells}, lang)


def intended(proposal: Mapping[str, Any], place: Place | None, known: Known, lang: str) -> str:
    if proposal['kind'] == GO and place is not None:
        return where(way(target(proposal), place, known), lang)
    return render(f'{KIND}{proposal["kind"]}', lang=lang)


def menu(council: Mapping[str, Any], place: Place | None, known: Known) -> Menu:
    """
    The answers a player may give and the places of the goes, best voted first, leaving out what the player's
    voice cannot win; a go stays, for a cell picked on the map is weighed anew.
    """
    leader = council.get('leader') or {}
    table = council['table']
    voice = council.get('voice')

    def won(votes: int, others: list[int]) -> bool:
        return voice is None or votes + voice >= max(others, default=0)

    def winnable(entry: Mapping[str, Any]) -> bool:
        return won(entry['votes'], [other['votes'] for other in table if other is not entry])

    answers = [Option(GO, None, leader.get('kind') == GO)]
    for kind in (STAY, WINTER):
        votes = sum(entry['votes'] for entry in table if entry['proposal']['kind'] == kind)
        others = [entry['votes'] for entry in table if entry['proposal']['kind'] != kind]
        if (kind != WINTER or council.get('winter')) and won(votes, others):
            answers.append(Option(kind, {'kind': kind}, leader.get('kind') == kind))
    answers.append(Option(ABSTAIN, SILENCE, False))
    goes = [entry for entry in table if entry['proposal']['kind'] == GO and winnable(entry)]
    levels = sorted({entry['votes'] for entry in goes}, reverse=True)[:LEVELS]
    # One place for each of the most voted levels, the leader first among its equals.
    chosen = [
        min((entry for entry in goes if entry['votes'] == votes), key=lambda entry: entry['proposal'] != leader)
        for votes in levels
    ]
    places = [
        Option(
            GO,
            entry['proposal'],
            entry['proposal'] == leader,
            None if place is None else way(target(entry['proposal']), place, known),
        )
        for entry in chosen
    ]
    return Menu(answers, places, place, council.get('place', True))


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
