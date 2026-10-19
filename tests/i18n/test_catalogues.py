import pytest
from fluent.syntax import FluentParser, ast
from fluent.syntax.visitor import Visitor

from dominion_theory.api.errors import UNIT_NOT_FOUND
from dominion_theory.client import review
from dominion_theory.client.lines import MESSAGES
from dominion_theory.content import load_params
from dominion_theory.content.loader import PRESET_NOT_FOUND
from dominion_theory.content.model import PARAMS_INVALID
from dominion_theory.core.errors import DominionError
from dominion_theory.db.profiles import LOCALE_UNKNOWN, LOCALES, PROFILE_NOT_FOUND
from dominion_theory.engine import EVENTS, REASONS, council
from dominion_theory.engine.band import STATES
from dominion_theory.engine.commands import GO, PROPOSALS
from dominion_theory.engine.events import SKILL, STATE
from dominion_theory.i18n import DATE, LANGUAGES, catalogue
from dominion_theory.runner import ERRORS

# Stated by docs/api/commands.md and docs/api/protocol.md, declared by no code yet.
SPECIFIED: set[str] = {
    'error-request-unreadable',
    'error-command-invalid',
    'people-lost',
}


class Variables(Visitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_VariableReference(self, node: ast.VariableReference) -> None:
        self.names.add(node.id.name)


def entries(lang: str) -> list[ast.EntryType]:
    return list(FluentParser().parse(catalogue(lang)).body)


def variables(lang: str) -> dict[str, set[str]]:
    found = {}
    for entry in entries(lang):
        if isinstance(entry, ast.Message):
            visitor = Variables()
            visitor.visit(entry)
            found[entry.id.name] = visitor.names
    return found


def in_use() -> set[str]:
    params = load_params()
    time = params.time
    names = {f'time-part-{part}' for part in time.day_parts} | {f'time-season-{season.name}' for season in time.seasons}
    names |= {f'biome-{biome}' for biome in params.biomes}
    names |= {f'resource-{resource}' for resource in params.resources}
    names |= {f'play-property-{name}' for era, held in params.eras for name in held.properties}
    names |= {f'{STATE}{state}' for state in STATES}
    names |= {f'encounter-{kind}' for kind in params.encounters.kinds}
    names |= {f'{SKILL}{skill}' for skill in params.skills}
    names |= {council.key({'kind': kind}) for kind in PROPOSALS if kind != GO}
    names.add(council.key(council.going((0, 0))))
    goes = (*params.biomes, *(f'{council.THROUGH}{biome}' for biome in params.biomes), council.UNKNOWN)
    names |= {f'proposal-go-{land}' for land in goes}
    names.add(council.key(None))
    names |= {f'{council.OCCASION}{occasion}' for occasion in council.OCCASIONS}
    people = params.units.band.people
    names |= {f'{review.STAGE}{name}' for name in people.stages} | {f'{review.ROLE}{name}' for name in people.roles}
    names |= {f'{review.WOUND}{name}' for name in people.injury.severities}
    errors = {*ERRORS, PRESET_NOT_FOUND, PARAMS_INVALID, LOCALE_UNKNOWN, PROFILE_NOT_FOUND, UNIT_NOT_FOUND}
    return {*EVENTS, *REASONS, DATE, *MESSAGES, *review.MESSAGES} | errors | names | SPECIFIED


def test_languages_are_those_of_a_profile() -> None:
    assert LANGUAGES == LOCALES


@pytest.mark.parametrize('lang', LANGUAGES)
def test_catalogue_reads_cleanly(lang: str) -> None:
    junk = [entry.content for entry in entries(lang) if isinstance(entry, ast.Junk)]

    assert junk == []


@pytest.mark.parametrize('lang', LANGUAGES)
def test_key_is_written_once(lang: str) -> None:
    keys = [entry.id.name for entry in entries(lang) if isinstance(entry, ast.Message)]

    assert sorted(keys) == sorted(set(keys))


@pytest.mark.parametrize('lang', LANGUAGES)
def test_every_key_in_use_exists(lang: str) -> None:
    assert in_use() - variables(lang).keys() == set()


@pytest.mark.parametrize('lang', LANGUAGES)
def test_no_key_that_nothing_uses(lang: str) -> None:
    assert variables(lang).keys() - in_use() == set()


def test_entry_takes_the_same_values_in_both_languages() -> None:
    english, russian = variables('en'), variables('ru')

    assert {key: english[key] for key in english.keys() & russian.keys()} == {
        key: russian[key] for key in english.keys() & russian.keys()
    }


@pytest.mark.parametrize('lang', LANGUAGES)
def test_event_asks_only_for_values_it_carries(lang: str) -> None:
    found = variables(lang)

    assert {key: found[key] - set(carried) for key, carried in EVENTS.items()} == dict.fromkeys(EVENTS, set())


def test_unknown_language_is_refused() -> None:
    with pytest.raises(DominionError) as raised:
        catalogue('xx')

    assert raised.value.message() == {'key': LOCALE_UNKNOWN, 'values': {'locale': 'xx'}}
