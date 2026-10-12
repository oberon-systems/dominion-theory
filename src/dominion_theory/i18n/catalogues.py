"""
The catalogues: Fluent files, one directory per language, and the words they give for a message.
"""

from collections.abc import Callable, Mapping
from functools import cache
from importlib.resources import files
from typing import Any

from fluent.runtime import FluentBundle, FluentResource
from fluent.runtime.types import FluentNone

from ..core import logger
from ..core.errors import DominionError

LANGUAGES: tuple[str, ...] = ('en', 'ru')
FALLBACK = 'en'
DATE = 'time-date'
LOCALE_UNKNOWN = 'error-locale-unknown'


def check_language(lang: str) -> str:
    if lang not in LANGUAGES:
        raise DominionError(LOCALE_UNKNOWN, locale=lang)
    return lang


@cache
def catalogue(lang: str) -> str:
    """
    Every file of one language as one text, the way a client loads it.
    """
    folder = files('dominion_theory.i18n') / 'locales' / check_language(lang)
    entries = sorted((entry for entry in folder.iterdir() if entry.name.endswith('.ftl')), key=lambda entry: entry.name)
    return '\n'.join(entry.read_text(encoding='utf-8') for entry in entries)


@cache
def _bundle(lang: str) -> FluentBundle:
    def name(area: str, identifier: object, form: str | None = None) -> object:
        key = f'{area}-{identifier}'
        return render(key, lang=lang) if form is None else _form(key, form, lang)

    functions: dict[str, Callable[..., Any]] = {'NAME': name}
    bundle = FluentBundle([lang], functions=functions, use_isolating=False)
    bundle.add_resource(FluentResource(catalogue(lang)))
    return bundle


def _form(key: str, form: str, lang: str) -> object:
    bundle = _bundle(lang)
    pattern = bundle.get_message(key).attributes.get(form) if bundle.has_message(key) else None
    if pattern is None:
        return FluentNone()
    return bundle.format_pattern(pattern)[0]


def _chain(lang: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((lang, FALLBACK)))


def _value(value: Any, lang: str) -> Any:
    if isinstance(value, Mapping):
        return render(DATE, value, lang)
    if isinstance(value, str):
        known = any(_bundle(tongue).has_message(value) for tongue in _chain(lang))
        return render(value, lang=lang) if known else value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return value
    return str(value)


def render(key: str, values: Mapping[str, Any] | None = None, lang: str = FALLBACK) -> str:
    """
    The words for a message. Missing in the language gives English, missing there gives the key.
    """
    for tongue in _chain(check_language(lang)):
        bundle = _bundle(tongue)
        pattern = bundle.get_message(key).value if bundle.has_message(key) else None
        if pattern is None:
            logger.warning('the message %s is missing in %s', key, tongue)
            continue
        given = {name: _value(value, lang) for name, value in (values or {}).items()}
        text, errors = bundle.format_pattern(pattern, given)
        for error in errors:
            logger.warning('the message %s in %s: %r', key, tongue, error)
        return str(text)
    return key
