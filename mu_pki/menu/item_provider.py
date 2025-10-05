from functools import cached_property
from itertools import chain
from typing import overload

from .item import ChoiceItem, Item


class ItemProvider:
    def __init__(self) -> None:
        self._items: list[Item] = []

    def append(self, item: Item):
        self._items.append(item)
        self.__dict__.pop("items", None)

    @cached_property
    def items(self):
        return [item for item in sorted(self._items)]

    @overload
    def __getitem__(self, i: slice) -> list[Item]: ...
    @overload
    def __getitem__(self, i: int) -> Item: ...

    def __getitem__(self, i):
        return self.items.__getitem__(i)


class ExactItemProvider(ItemProvider):
    @cached_property
    def items(self):
        return self._items


class ChoiceItemProvider(ItemProvider):
    def __init__(self, base: set[ChoiceItem] | None = None) -> None:
        super().__init__()

        self.base = base if base else set()
        self.__items: set[ChoiceItem] = set()

    def append(self, item: Item):
        raise Exception("not supported")

    def input(self, i: int):
        item = self.items[i]
        if i < len(self.base):
            item.switch()
            return

        self.__items.remove(item)
        self.__dict__.pop("items", None)

    def extra(self, item: ChoiceItem):
        if i := self.items.index(item):
            return self.input(i)

        self.__items.add(item)
        self.__dict__.pop("items", None)

    @cached_property
    def items(self):  # type: ignore
        return [item for item in chain(self.base, sorted(self.__items - self.base))]
