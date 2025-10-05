import curses

from wcwidth import wcswidth

from mu_pki.globals import G

stdscr = curses.initscr()


class Display:
    def __init__(self) -> None:
        max_h, max_w = stdscr.getmaxyx()
        max_w -= 4
        max_h -= 2

        self.screen = curses.newwin(max_h, max_w, 1, 2)
        self.max_w = max_w - 2
        self.max_h = max_h - 2
        self.box_w = self.max_w - 2 * G.IDENT - 4
        self.div = f"├{'┄' * (self.max_w)}┤"
        self.footer_div = f"├{'─' * (self.max_w)}┤"

        self.box = self.new_box(1)

    def add_line(self, line: str, x: int = 0):
        self.screen.addstr(self.line_no, x, line)
        self.line_no += 1

    def clear(self):
        self.line_no = 1
        self.screen.clear()
        self.screen.border()
        curses.curs_set(0)
        curses.noecho()

    def block_with_empty(self, y_ava: int):
        dp.add_line(dp.div)
        notice = "* empty *"
        dp.screen.addstr(self.line_no + (y_ava // 2), (dp.max_w - wcswidth(notice)) // 2, notice)
        dp.line_no += y_ava

    def new_box(self, hight: int):
        y = (self.max_h - hight) // 2

        box = self.screen.subwin(hight + 2, self.box_w + 2, y, G.IDENT + 4)
        box.clear()
        box.border()

        return box

    def show_notif(self, text: str):
        lines = text.strip().split("\n")
        box = self.new_box(len(lines))
        for i, line in enumerate(lines, 1):
            box.addstr(i, G.IDENT, line)

        box.refresh()

        box.getch()

        box.clear()
        del box

    def show_input_state(self, prompt: str, buff: list[str], expected_len: int = 0):
        self.box.clear()
        self.box.border()

        self.box.addstr(0, G.IDENT, f" [ {prompt} ] ")
        # TODO: wch support
        self.box.addnstr(
            1,
            G.IDENT,
            "".join(buff[-(self.box_w - G.IDENT) :]),
            self.box_w - G.IDENT,
        )
        if expected_len and (current_len := len(buff)) < expected_len:
            self.box.addstr("_" * (expected_len - current_len))

        self.box.refresh()


dp = Display()
