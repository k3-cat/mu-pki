import curses
from functools import cached_property
from pathlib import Path

from mu_pki.cert import CertWrapper, load_or_init_root_ca
from mu_pki.globals import G
from mu_pki.menu import sel_menu, show_cert
from mu_pki.menu.display import dp
from mu_pki.menu.item import Item
from mu_pki.menu.item_provider import ItemProvider
from mu_pki.menu.select import sel_sl

_CERT_OPT = {"x"}
_CA_OPT = {"d", "n"}


class FilenameItem(Item):
    DIR_NOTE = "@"
    MISS_NOTE = "# "

    def __init__(self, text: str, is_dir: bool, is_miss) -> None:
        self.name = text
        self.is_dir = is_dir
        self.is_miss = is_miss

    @cached_property
    def _text(self):
        filename = f"{self.DIR_NOTE if self.is_dir else ''}{self.name}"
        return f"{self.MISS_NOTE if self.is_miss else ''}{filename}"


def access_cert(cp: CertWrapper):
    while True:
        opt = set(_CERT_OPT)
        opt_itp = ItemProvider()
        opt_itp.append(Item("x - return"))
        if cp.isCA:
            opt |= _CA_OPT
            opt_itp.append(Item("d - new directory"))
            opt_itp.append(Item("n - new item"))

        if cp.key:
            opt.add("p")
            opt_itp.append(Item("p - print key"))

        else:
            opt.add("v")
            opt_itp.append(Item("v - verify key"))

        child_itp = None
        if cp.isCA:
            cp.meta.update()
            child_itp = ItemProvider()
            for name, info in cp.meta.certs.items():
                child_itp.append(FilenameItem(name, info.id in cp.meta.ca, info.id in cp.meta.miss))

        show_cert(cp, opt_itp, child_itp)
        sel = sel_menu(opt, child_itp)

        if sel == "x":
            return

        if sel == "v":
            cp.key.load()
            continue

        if sel == "p":
            dp.show_notif(cp.key.pem.decode())
            continue

        if isinstance(sel, int) and child_itp:
            name = child_itp[sel].name  # type: ignore
            if cp.meta.certs[name].id in cp.meta.miss:
                dp.show_notif(f"File for cert '{name}' is missing.")
                continue

            next_cp = cp.get_child(name)
            next_cp.load()

        else:
            if sel == "n":
                is_directory = False
                name = sel_sl("cert name")

            elif sel == "d":
                is_directory = True
                name = sel_sl("dir name")

            else:
                raise Exception()

            if name in cp.meta.certs:
                dp.show_notif(f"Cert with '{name}' already exist.")
                continue

            next_cp = cp.get_child(name)
            next_cp.create(is_directory)

        access_cert(next_cp)


def main(root_dir: Path):
    try:
        G.ROOT_DIR = root_dir

        G.ROOT_DIR.mkdir(mode=750, parents=True, exist_ok=True)
        root = load_or_init_root_ca()

        access_cert(root)

    finally:
        curses.endwin()


if __name__ == "__main__":
    main(Path(__file__).parents[1] / "store")
