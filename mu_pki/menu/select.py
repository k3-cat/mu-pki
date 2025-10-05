import math
from typing import overload

from mu_pki.menu.item_provider import ItemProvider

from .display import dp


def sel_sl(prompt: str):
    buff: list[str] = []
    while True:
        dp.show_input_state(prompt, buff)

        ch = dp.screen.get_wch()
        if ch == "\n" and buff:
            return "".join(buff).strip()

        if ch == "\x08" and buff:
            buff.pop()

        elif isinstance(ch, str) and ch.isprintable():
            buff.append(ch)


def sel_sl_with_default(prompt: str, default: str):
    # TODO: trim default if too long? or display in new line?
    val = sel_sl(f"{prompt} [{default}]")
    return val if val else default


def _sel_num(length: int, init_key: str | None):
    prompt = f"input a {length}-digits number"
    buff: list[str] = []
    if init_key:
        buff.append(init_key)

    while True:
        if len(buff) == length:
            return int("".join(buff))

        dp.show_input_state(prompt, buff, length)
        ch = dp.screen.getkey()
        if ch.isdigit():
            buff.append(ch)

        elif ch == "\x08" and buff:
            buff.pop()

        elif ch == "\n" and buff:
            length = len(buff)


@overload
def sel_menu(opt: set[str], itp: None) -> str: ...
@overload
def sel_menu(opt: set[str], itp: ItemProvider) -> str | int: ...


def sel_menu(opt, itp):
    max_idx = len(itp.items) - 1 if itp else None
    while True:
        ch = dp.screen.getkey()
        if ch in opt:
            return ch

        if max_idx is None or not ch.isdigit():
            continue

        buff_len = math.ceil(math.log10(max_idx + 2))
        while True:
            sel = _sel_num(buff_len, ch)
            if sel <= max_idx:
                return sel

            dp.show_notif(f"Selected index '{sel}' out of range (valid range: 0~{max_idx}).")
            ch = None
