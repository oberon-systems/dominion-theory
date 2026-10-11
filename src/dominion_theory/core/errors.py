"""
The base error: a message key with values, never text for a person.
"""


class DominionError(Exception):
    """
    Anything a player may read is raised as a key and its values.
    """

    def __init__(self, key: str, **values: object) -> None:
        super().__init__(key)
        self.key = key
        self.values = values

    def message(self) -> dict[str, object]:
        return {'key': self.key, 'values': dict(self.values)}
