import math
from dataclasses import dataclass

from wcwidth import wcswidth

from mu_pki.globals import G

from . import stats
from .display import Display
from .item_provider import ItemProvider

# ---
# ava: available
# avg: average
# cnt: count
# col: column
# idx: index
# lim: limit
# pln: plan
# tot: total


COL_EX = wcswidth(G.COL_SPACER)
IDX_EX = wcswidth(G.IDX_SPACER)


@dataclass
class WPln:
    max_item: int
    raw_item: float
    idx: int
    idx_ex: int
    col_ex: int

    item: int = 0

    @property
    def raw_tot(self):
        return self.raw_item + self.idx + self.idx_ex + self.col_ex

    @property
    def max_tot(self):
        return self.max_item + self.idx + self.idx_ex + self.col_ex

    @property
    def tot(self):
        return self.item + self.idx + self.idx_ex + self.col_ex

    def constrain_tot(self, tot_w: float):
        self.raw_item = tot_w - self.idx - self.idx_ex - self.col_ex
        self.item = round(self.raw_item)

    def scale_raw_by_factor(self, factor: float):
        self.constrain_tot(self.raw_tot * factor)


class ItemGrid:
    def __init__(self, dp: Display, index: bool, provider: ItemProvider) -> None:
        self.max_w = dp.max_w
        self.max_h = dp.max_h
        self.has_idx = index
        self.itp: ItemProvider = provider

        self.hight: int
        self.plns: list[WPln]

    def plan_col(self, h: int = 0, is_fixed: bool = False):
        item_cnt = len(self.itp.items)

        # --- predict ---
        if h <= 0:
            avg_w = (
                stats.ci([i.len for i in self.itp.items], avg_only=True)
                + stats.predict_index_avg_len(item_cnt)
                + IDX_EX
                + COL_EX
            )
            h = math.ceil(item_cnt / (self.max_w / avg_w))

        h = min(h, self.max_h)

        # --- explore & backtrack ---
        last_successful_result: list[WPln] | None = None
        while True:
            self.plns = []
            col_cnt = math.ceil(item_cnt / h)
            for i in range(col_cnt - 1):
                end = h * (i + 1)
                item_widths = [i.len for i in self.itp[end - h : end]]
                self.plns.append(
                    WPln(
                        max(item_widths),
                        stats.ci(item_widths),
                        math.ceil(math.log10(end + 1)) if self.has_idx else 0,
                        (IDX_EX if self.has_idx else 0),
                        COL_EX,
                    )
                )

            item_widths = [i.len for i in self.itp[h * (col_cnt - 1) :]]
            self.plns.append(
                WPln(
                    max(item_widths),
                    stats.ci(item_widths),
                    math.ceil(math.log10(item_cnt + 1)) if self.has_idx else 0,
                    (IDX_EX if self.has_idx else 0),
                    COL_EX,
                )
            )

            if sum(pln.raw_tot for pln in self.plns) <= self.max_w:
                if is_fixed or h == 1:
                    break

                last_successful_result = self.plns
                h -= 1
                continue

            h += 1
            if last_successful_result:
                self.plns = last_successful_result
                break

            if (not is_fixed) and (h <= self.max_h):
                continue

            raise NotImplementedError("Paging required")

        self.hight = h

        if col_cnt == 1:
            self.plns[0].constrain_tot(self.max_w)
            return

        # --- scale up, shrink & spread ---
        factor = self.max_w / sum(p.raw_tot for p in self.plns)
        ordered_cols = sorted(self.plns, key=lambda p: p.max_item - p.raw_item)
        pool = self.max_w
        target = pool / col_cnt
        for i, pln in enumerate(ordered_cols):
            pln.scale_raw_by_factor(factor)
            tot = pln.max_tot
            if target < tot:
                tot = pln.raw_tot

            if tot < target:
                extra = target - tot
            else:
                extra = target - min(tot, pool)

            pln.constrain_tot(target - extra)
            pool -= pln.tot
            target += extra / max(1, (col_cnt - i - 1))

        if pool:
            # previous step garanted no overflows
            for i, pln in enumerate(ordered_cols[:-1]):
                extra = round(pool / (col_cnt - i - 1))
                pln.item += extra
                pool -= extra

    def render(self, dp: Display):
        item_cnt = len(self.itp.items)
        col_cnt = len(self.plns)
        for y in range(self.hight):
            x = G.IDENT
            for col_no, pln in enumerate(self.plns):
                n = col_no * self.hight + y
                if item_cnt < n + 1:
                    break

                item = self.itp[n]
                if self.has_idx:
                    text = f"{n:>{pln.idx}}{G.IDX_SPACER}{item.text}"
                else:
                    text = item.text

                dp.screen.addnstr(dp.line_no, x, text, pln.item)
                x += pln.tot

                if pln.item < item.len:
                    dp.screen.addch(dp.line_no, x - pln.col_ex - 1, "*")

                if col_no < col_cnt - 1:
                    dp.screen.addstr(dp.line_no, x - COL_EX, G.COL_SPACER)

            dp.line_no += 1
