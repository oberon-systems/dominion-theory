"""
An update as a line of text: the date of the game, then the words of its events.
"""

from collections.abc import Mapping
from typing import Any

from ..i18n import DATE, render


def words(message: Mapping[str, Any], lang: str) -> str:
    return render(message['key'], message.get('values'), lang)


def line(update: Mapping[str, Any], lang: str) -> str:
    date = render(DATE, update['date'], lang)
    events = ' '.join(words(event, lang) for event in update['events'])
    return f'{date}: {events}' if events else date
