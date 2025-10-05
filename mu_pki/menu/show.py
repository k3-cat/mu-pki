from typing import TYPE_CHECKING

from cryptography import x509
from wcwidth import wcswidth

from .display import dp
from .item import Item
from .item_grid import ItemGrid
from .item_provider import ExactItemProvider, ItemProvider

if TYPE_CHECKING:
    from mu_pki.cert import CertWrapper


def show_cert(cp: "CertWrapper", opt_itp: ItemProvider, child_itp: ItemProvider | None):
    dp.clear()

    akid_warn = ""
    if cp != cp.parent:
        if not ((akid := cp.akid) and akid.key_identifier):
            akid_warn = " | MISSING AKId"

        elif akid.key_identifier != cp.parent.skid.key_identifier:
            akid_warn = " | AKId MISSMATCH"

    title = f" [ {cp.name}{akid_warn} ] "
    dp.screen.addstr(0, (dp.max_w - wcswidth(title)) // 2, title)

    bi_itp = ExactItemProvider()
    bi_itp.append(Item(f"sub: {cp.sub}"))
    bi_itp.append(Item(f"nbf: {cp.cert.not_valid_before_utc}"))
    bi_itp.append(Item(f"exp: {cp.cert.not_valid_after_utc}"))
    bi_itp.append(Item(f"skid: {cp.skid.key_identifier.hex()}"))
    bi_itp.append(Item(f"sn: {cp.cert.serial_number:x}"))
    bi_itp.append(Item(f"sha256: {cp.sha256.hex()}"))

    bi_grid = ItemGrid(dp, False, bi_itp)
    bi_grid.plan_col()

    opt_grid = ItemGrid(dp, False, opt_itp)
    opt_grid.plan_col()

    y_ava = dp.max_h - bi_grid.hight - 1 - opt_grid.hight - 1

    eku_grid: ItemGrid | None = None
    if ekus := cp.get_ext(x509.ExtendedKeyUsage):
        eku_itp = ItemProvider()
        for eku in ekus:
            eku_itp.append(Item(f"{eku.dotted_string} ({eku._name})"))

        eku_grid = ItemGrid(dp, False, eku_itp)
        if child_itp and len(child_itp.items):
            eku_grid.plan_col()
        else:
            eku_grid.plan_col(y_ava, True)

        y_ava -= eku_grid.hight - 1

    child_grid: ItemGrid | None = None
    if child_itp and len(child_itp.items):
        child_grid = ItemGrid(dp, True, child_itp)
        child_grid.plan_col(y_ava, True)

    # --- rendering ---
    bi_grid.render(dp)
    if eku_grid:
        dp.add_line(dp.div)
        eku_grid.render(dp)

    if child_grid:
        dp.add_line(dp.div)
        child_grid.render(dp)

    elif cp.isCA or not eku_grid:
        dp.block_with_empty(y_ava)

    dp.add_line(dp.footer_div)
    opt_grid.render(dp)

    dp.screen.refresh()


def show_ekus(opt_itp: ItemProvider, ekus_itp: ItemProvider):
    dp.clear()

    opt_grid = ItemGrid(dp, False, opt_itp)
    opt_grid.plan_col()

    y_ava = dp.max_h - opt_grid.hight - 1

    ekus_grid = ItemGrid(dp, True, ekus_itp)
    ekus_grid.plan_col(y_ava, True)

    # --- rendering ---
    ekus_grid.render(dp)
    dp.add_line(dp.footer_div)
    opt_grid.render(dp)

    dp.screen.refresh()
