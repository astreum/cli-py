import logging
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, List, Optional, Tuple

from utils.config import persist_node_latest_block_hash
from astreum import Node
from modes.tui.render import render_app
from modes.tui.pages.accounts.create import AccountCreatePage
from modes.tui.pages.accounts.list import AccountListPage
from modes.tui.pages.menu import MenuPage
from modes.tui.pages.search import SearchPage
from modes.tui.pages.settings import SettingsPage
from modes.tui.pages.terminal import TerminalPage
from modes.tui.pages.transaction import TransactionPage

if os.name == "nt":
    import msvcrt
else:
    import select
    import termios
    import tty

HEADER_LINES = [
    " \u2588\u2588\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557 \u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2550\u255d  \u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2551",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2588\u2557     \u2588\u2588\u2551    \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2588\u2588\u2588\u2557   \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2554\u2588\u2588\u2588\u2588\u2554\u2588\u2588\u2551",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551  \u255a\u2550\u2550\u2550\u2588\u2588\u2557    \u2588\u2588\u2551    \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u255d   \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2551\u255a\u2588\u2588\u2554\u255d\u2588\u2588\u2551",
    "\u2588\u2588\u2551  \u2588\u2588\u2551 \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d    \u2588\u2588\u2551    \u2588\u2588\u2551  \u2588\u2588\u2551 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2551 \u255a\u2550\u255d \u2588\u2588\u2551",
    "\u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d     \u255a\u2550\u255d    \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d  \u255a\u2550\u2550\u2550\u2550\u2550\u255d  \u255a\u2550\u255d     \u255a\u2550\u255d",
    "",
    " \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2557      \u2588\u2588\u2557",
    "\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d  \u2588\u2588\u2551      \u2588\u2588\u2551",
    "\u2588\u2588\u2551       \u2588\u2588\u2551      \u2588\u2588\u2551",
    "\u2588\u2588\u2551       \u2588\u2588\u2551      \u2588\u2588\u2551",
    "\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2551",
    " \u255a\u2550\u2550\u2550\u2550\u2550\u255d  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d",
]
FOOTER_TEXT = "Up/Down to navigate \u2022 Enter to select \u2022 Esc to return"

class FooterLogHandler(logging.Handler):
    """Send node log lines into the app footer buffer."""

    def __init__(self, app: "App") -> None:
        super().__init__(level=logging.INFO)
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self.app.push_log_line(message)


class App:
    lines: List[str]
    header_lines: Optional[Tuple[int, int]]
    body_lines: Optional[Tuple[int, int]]
    footer_lines: Optional[Tuple[int, int]]
    log_lines: Deque[str]
    flash_message: None

    def __init__(self, *, data_dir: Path, configs: dict[str, Any]) -> None:
        self.data_dir = data_dir
        self.configs = configs
        self.node = Node(config=self.configs["node"])
        
        self.header_block = HEADER_LINES
        self.footer_text = f"\x1b[90m{FOOTER_TEXT}\x1b[0m"
        self.pages = {
            "menu": MenuPage(),
            "search": SearchPage(),
            "account_list": AccountListPage(),
            "account_create": AccountCreatePage(),
            "transaction_create": TransactionPage(),
            "terminal": TerminalPage(),
            "settings": SettingsPage(),
        }

        self.active_view = "menu"
        self.previous_view = None
        self.input_focus = False
        self.cursor_effect_switch = False

        self.lines = []
        self.line_offset = 0
        self.header_lines = None
        self.footer_lines = None
        self.flash_message = None
        self.log_lines = deque(maxlen=5)
        self.log_event = threading.Event()
        self._install_footer_logger()
        self._run_cli_startup_actions()
        
        self.should_exit = False

    def _install_footer_logger(self) -> None:
        """Attach footer log handler to node logger if available."""
        self.push_log_line("installing logger")
        node_logger = getattr(self.node, "logger", None)
        base_logger = getattr(node_logger, "logger", None)
        if base_logger is None:
            self.push_log_line("Node logger unavailable; footer logs disabled.")
            return
        handler = FooterLogHandler(app=self)
        handler.setFormatter(logging.Formatter("%(message)s"))
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.INFO)

    def _run_cli_startup_actions(self) -> None:
        """Invoke optional CLI startup actions configured via settings."""
        cli_config = self.configs["cli"]

        if cli_config.get("on_startup_connect_node"):
            self.push_log_line("connecting node")
            try:
                self.node.connect()
                self.push_log_line("node connected")
            except Exception as exc:
                self.push_log_line(f"node connect failed: {exc}")

        if cli_config.get("on_startup_validate_blockchain"):
            self.push_log_line("validating blockchain")
            try:
                self.node.validate()
                self.push_log_line("blockchain validation complete")
            except Exception as exc:
                self.push_log_line(f"blockchain validation failed: {exc}")

    def push_log_line(self, message: str) -> None:
        clean = " ".join(message.split())
        self.log_lines.append(clean)
        self.log_event.set()

    def handle_special_key(self, code: str):
        direction_map = {
            'H': "up",
            'P': "down",
            'K': "left",
            'M': "right",
            'A': "up",
            'B': "down",
            'D': "left",
            'C': "right",
        }
        direction = direction_map.get(code)
        if direction is None:
            return

        if self.input_focus:
            element = self.element_in_focus()
            if element is None:
                return
            
            element.navigate_input(direction=direction)
        else:
            if direction == "up":
                if self.line_offset > 0:
                    self.line_offset -= 1
                self.pages[self.active_view].navigate(forward=False)
                return
            if direction == "down":
                max_offset = max(0, len(self.lines) - self.window_rows)
                if self.line_offset < max_offset:
                    self.line_offset += 1
                self.pages[self.active_view].navigate(forward=True)
                return

    def handle_enter(self) -> bool:
        element = self.element_in_focus()
        if element is None:
            return

        if element.input:
            if self.input_focus:
                element.handle_input_enter()

            else:
                self.cursor_effect_switch = True
                self.input_focus = True

        elif element.next:
            self.previous_view = self.active_view
            self.active_view = element.next
        
        elif element.action:
            element.action(app=self)

    def handle_delete(self):
        element = self.element_in_focus()
        if element is None:
            return

        if element.input:
            if self.input_focus:
                element.handle_input_delete()
        
    def handle_return(self):
        if self.flash_message:
            self.flash_message = None
            
        if self.input_focus:
            self.cursor_effect_switch = False
            self.input_focus = False
        
        # elif self.previous_view:
        #     current_view = self.active_view
        #     next_view = self.previous_view
        #     self.previous_view = current_view
        #     self.active_view = next_view

        else:
            self.active_view = "menu"
    
    def handle_char(self, key):
        if not self.input_focus:
            return

        element = self.element_in_focus()
        if element is None:
            return
            
        if not hasattr(element, 'handle_input'):
            return

        element.handle_input(char=key)

    def element_in_focus(self) -> Optional["PageElement"]:
        page = self.pages.get(self.active_view)
        if page is None:
            return None
            
        if not hasattr(page, 'elements') or not hasattr(page, 'index'):
            return None
            
        if not isinstance(page.elements, list):
            return None
            
        if not (0 <= page.index < len(page.elements)):
            return None
        
        return page.elements[page.index]


class KeyboardInput:
    def __init__(self) -> None:
        self._is_windows = os.name == "nt"
        self._fd: Optional[int] = None
        self._old_settings: Optional[List[Any]] = None

    def __enter__(self) -> "KeyboardInput":
        if not self._is_windows:
            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._is_windows and self._fd is not None and self._old_settings is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)

    def read_event(self) -> Optional[Tuple[str, str]]:
        if self._is_windows:
            if not msvcrt.kbhit():
                return None
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                extended = msvcrt.getwch()
                return ("special", extended)
            return ("char", key)

        if self._fd is None:
            return None

        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None

        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                return ("char", ch)
            next_ch = sys.stdin.read(1)
            if next_ch != "[":
                return ("char", ch)
            if not select.select([sys.stdin], [], [], 0)[0]:
                return ("char", ch)
            arrow = sys.stdin.read(1)
            return ("special", arrow)
        return ("char", ch)


def run_tui(*, data_dir: Path, configs: dict[str, Any]) -> int:
    app = App(data_dir=data_dir, configs=configs)

    sys.stdout.write(f"\033[?1049h\033[?25l")
    sys.stdout.flush()
    render_app(app)

    cursor_effect = time.time()
    CURSOR_SPEED = 0.5
    RENDER_SPEED = 0.03
    render_time = time.time()

    try:
        with KeyboardInput() as keyboard:
            while not app.should_exit:
                now = time.time()
                updated = False

                if app.log_event.is_set():
                    render_app(app, cursor_effect=app.cursor_effect_switch)
                    app.log_event.clear()

                if app.input_focus:
                    if now - render_time >= RENDER_SPEED:
                        render_app(app, cursor_effect=app.cursor_effect_switch)
                        render_time = now

                    if now - cursor_effect >= CURSOR_SPEED:
                        app.cursor_effect_switch = not app.cursor_effect_switch
                        cursor_effect = now
                        updated = True

                event = keyboard.read_event()
                if event is not None:
                    kind, key = event
                    if kind == "special":
                        app.handle_special_key(key)
                    elif key in ("\r", "\n"):
                        app.handle_enter()
                    elif key == "\x1b":
                        app.handle_return()
                    elif key in ("\x08", "\x7f"):
                        app.handle_delete()
                    else:
                        app.handle_char(key)
                    updated = True

                if updated:
                    render_app(app, cursor_effect=app.cursor_effect_switch)

                time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        latest_hash = app.node.latest_block_hash
        if latest_hash is not None:
            persist_node_latest_block_hash(
                data_dir=app.data_dir,
                configs=app.configs,
                latest_block_hash=latest_hash,
            )
        sys.stdout.write(f"\033[?1049l\033[?25h")
        sys.stdout.flush()

    return 0
