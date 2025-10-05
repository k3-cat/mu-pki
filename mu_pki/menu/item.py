from functools import cached_property

from wcwidth import wcswidth


class Item:
    def __init__(self, text: str) -> None:
        self._text = text

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Item):
            return False

        return self._text.__eq__(value._text)

    def __gt__(self, value):
        if not isinstance(value, Item):
            return False

        return self._text.__gt__(value._text)

    def __lt__(self, value):
        if not isinstance(value, Item):
            return False

        return self._text.__lt__(value._text)

    def __hash__(self) -> int:
        return self._text.__hash__()

    @cached_property
    def len(self):
        return wcswidth(self.text)

    @cached_property
    def text(self):
        return self._text


class ChoiceItem(Item):
    ON = "[X] "
    OFF = "[ ] "

    def __init__(self, text: str, init_state: bool) -> None:
        super().__init__(text)

        self.state = init_state

    @property
    def text(self):  # type: ignore
        return f"{self.ON if self.state else self.OFF}{self._text}"

    def switch(self):
        self.state = not self.state
