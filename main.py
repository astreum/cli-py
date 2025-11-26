import argparse
import msvcrt
import sys
import time
import uuid
from typing import List, Optional, Tuple

from app.config import load_config
from app.data import ensure_data_dir
from app.render import render_app
from astreum._node import Node, Expr
from evaluation import load_script_to_environment
from evaluation.expression import expression_from_string
from pages.accounts.create import AccountCreatePage
from pages.accounts.list import AccountListPage
from pages.definitions.create import DefinitionCreatePage
from pages.definitions.list import DefinitionCreatePage as DefinitionListPage
from pages.menu import MenuPage
from pages.search import SearchPage
from pages.settings import SettingsPage
from pages.terminal import TerminalPage
from pages.transaction import TransactionPage

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


class App:
    lines: List[str]
    header_lines: Optional[Tuple[int, int]]
    body_lines: Optional[Tuple[int, int]]
    footer_lines: Optional[Tuple[int, int]]
    flash_message: None

    def __init__(self) -> None:
        self.data_dir = ensure_data_dir()

        self.configs = load_config(self.data_dir)
        self.node = Node(self.configs["node"])
        
        self.header_block = HEADER_LINES
        self.footer_text = f"\x1b[90m{FOOTER_TEXT}\x1b[0m"
        self.pages = {
            "menu": MenuPage(),
            "search": SearchPage(),
            "account_list": AccountListPage(),
            "account_create": AccountCreatePage(),
            "transaction_create": TransactionPage(),
            "definition_list": DefinitionListPage(),
            "definition_create": DefinitionCreatePage(),
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
        
        self.should_exit = False

    def handle_special_key(self, code: str):
        direction_map = {
            'H': "up",
            'P': "down",
            'K': "left",
            'M': "right"
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
        
        elif self.previous_view:
            current_view = self.active_view
            next_view = self.previous_view
            self.previous_view = current_view
            self.active_view = next_view
    
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
    
def run_app() -> int:
    app = App()

    sys.stdout.write(f"\033[?1049h\033[?25l")
    sys.stdout.flush()
    render_app(app)

    cursor_effect = time.time()
    CURSOR_SPEED = 0.5
    RENDER_SPEED = 0.03
    render_time = time.time()

    try:
        while not app.should_exit:
            now = time.time()
            updated = False

            if app.input_focus:
                
                if now - render_time >= RENDER_SPEED:
                    render_app(app, cursor_effect=app.cursor_effect_switch)
                    render_time = now

                if now - cursor_effect >= CURSOR_SPEED:
                    app.cursor_effect_switch = not app.cursor_effect_switch
                    cursor_effect = now
                    updated = True

            if msvcrt.kbhit():
                key = msvcrt.getwch()

                if key in ("\x00", "\xe0"):
                    extended = msvcrt.getwch()
                    app.handle_special_key(extended)
                elif key in ("\r", "\n"):
                    app.handle_enter()
                elif key == "\x1b":
                    app.handle_return()
                elif key in ('\x08', '\x7f'):
                    app.handle_delete()
                else:
                    app.handle_char(key)

                updated = True

            if updated:
                render_app(app, cursor_effect=app.cursor_effect_switch)

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass

    sys.stdout.write(f"\033[?1049l\033[?25h")
    sys.stdout.flush()

    return 0


def run_eval(script: Optional[str], entry_expr_str: Optional[str]) -> int:
    data_dir = ensure_data_dir()
    configs = load_config(data_dir)
    node = Node(configs["node"])

    evaluated_expr = None
    env_id: Optional[uuid.UUID] = None

    if script is not None:
        env = load_script_to_environment(script=script)
        env_id = uuid.uuid4()
        node.environments[env_id] = env

    try:
        match (script is not None, entry_expr_str is not None):
            case (True, True):
                expr = expression_from_string(source=entry_expr_str)
                evaluated_expr = node.high_eval(expr=expr, env_id=env_id)
            case (True, False):
                expr = Expr.Symbol("main")
                evaluated_expr = node.high_eval(expr=expr, env_id=env_id)
            case (False, True):
                expr = expression_from_string(source=entry_expr_str)
                evaluated_expr = node.high_eval(expr=expr)
            case (False, False):
                sys.stdout.write("Eval command requires --script or --expr.\n")
                sys.stdout.flush()
                return 1
    finally:
        if env_id is not None:
            node.environments.pop(env_id, None)

    if evaluated_expr is not None:
        sys.stdout.write(f"{evaluated_expr}\n")
        sys.stdout.flush()
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Astreum CLI")
    parser.add_argument(
        "--eval",
        dest="eval_mode",
        action="store_true",
        help="Enable evaluation mode instead of launching the GUI",
    )
    parser.add_argument("--script", type=str, help="Path to a script file", default=None)
    parser.add_argument(
        "--expr",
        type=str,
        help="Postfix expression to evaluate (e.g., '(a b main)')",
        default=None,
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.eval_mode:
        return run_eval(script=args.script, entry_expr_str=args.expr)

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
