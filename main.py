import msvcrt
import os
import platform
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from astreum._node import Node

from accounts import create_account
from definitions import save_definition
from views import (
    AddDefinitionPage,
    CreateAccountPage,
    DefinitionListPage,
    ListAccountsPage,
)

MENU_LABELS = [
    "Search",
    "List Accounts",
    "Create Account",
    "Create Transaction",
    "List definitions",
    "Add a Definition",
    "Terminal",
    "Settings",
    "Quit",
]
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
FOOTER_TEXT = "Tab to select \u2022 Enter to select \u2022 Esc to return"


def ensure_data_dir() -> Path:
    """Ensure the data directory structure exists and return its path."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / "Astreum" / "cli-py"
    target.mkdir(parents=True, exist_ok=True)
    for folder in ("accounts", "definitions", "atoms"):
        (target / folder).mkdir(exist_ok=True)
    settings_path = target / "settings.json"
    if not settings_path.exists():
        settings_path.write_text("{}\n", encoding="utf-8")
    return target


class SelectionList:
    """Reusable helper to manage selection state across views."""

    def __init__(
        self,
        labels: List[str],
        active_prefix: str = "> ",
        inactive_prefix: str = "  ",
    ) -> None:
        self._labels = labels
        self._active_prefix = active_prefix
        self._inactive_prefix = inactive_prefix
        self.index = 0 if labels else -1

    def move(self, delta: int) -> None:
        if not self._labels:
            self.index = -1
            return
        self.index = (self.index + delta) % len(self._labels)

    def advance(self) -> None:
        self.move(1)

    def set_index(self, index: int) -> None:
        if not self._labels:
            self.index = -1
            return
        if 0 <= index < len(self._labels):
            self.index = index

    def current(self) -> Optional[str]:
        if self.index < 0 or self.index >= len(self._labels):
            return None
        return self._labels[self.index]

    def render_lines(self) -> List[str]:
        lines: List[str] = []
        for idx, label in enumerate(self._labels):
            prefix = self._active_prefix if idx == self.index else self._inactive_prefix
            lines.append(f"{prefix}{label}")
        return lines

    @property
    def labels(self) -> List[str]:
        return self._labels


class SettingsPage:
    """Display readonly configuration details."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def update_data_dir(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def render_lines(self) -> List[str]:
        return [
            "\x1b[1mSettings\x1b[0m",
            "",
            f"Data directory: {self._data_dir}",
        ]


class App:
    lines: List[str]
    header_lines: Optional[Tuple[int, int]]  # (start row, end row)
    body_lines: Optional[Tuple[int, int]]  # (start row, end row)
    footer_lines: Optional[Tuple[int, int]]  # (start row, end row)
    cursor: Optional[Tuple[int, int]]  # (row, col) 0-based

    def __init__(self) -> None:
        self.data_dir = ensure_data_dir()
        self.node = Node({"cold_storage_path": str(self.data_dir / "atoms")})
        self.header_block = HEADER_LINES + ["(c) Astreum Foundation"]
        self.footer_text = f"\x1b[90m{FOOTER_TEXT}\x1b[0m"
        self.menu = SelectionList(MENU_LABELS)
        self.create_account = CreateAccountPage()
        self.list_accounts = ListAccountsPage()
        self.add_definition = AddDefinitionPage()
        self.definition_list = DefinitionListPage()
        self.settings_page = SettingsPage(self.data_dir)
        self.active_view = "menu"
        self.lines = []
        self.header_lines = None
        self.body_lines = None
        self.footer_lines = None
        self.cursor = None

    def switch_view(self, view: str) -> None:
        if view == "create_account":
            self.active_view = "create_account"
            self.create_account.prepare_for_entry()
        elif view == "list_accounts":
            self.active_view = "list_accounts"
            self.list_accounts.refresh(self.data_dir)
        elif view == "list_definitions":
            self.active_view = "list_definitions"
            self.definition_list.refresh(self.data_dir)
        elif view == "add_definition":
            self.active_view = "add_definition"
            self.add_definition.prepare_for_entry()
        elif view == "settings":
            self.active_view = "settings"
            self.settings_page.update_data_dir(self.data_dir)
        else:
            self.active_view = "menu"

    def advance_selection(self) -> None:
        if self.active_view == "menu":
            self.menu.advance()
        elif self.active_view == "list_definitions":
            self.definition_list.move(1)
        elif self.active_view == "create_account":
            self.create_account.cycle_focus()
        elif self.active_view == "add_definition":
            self.add_definition.cycle_focus()

    def handle_special_key(self, code: str) -> bool:
        """Handle arrow-key style navigation from msvcrt."""
        if code in ("H", "K"):
            return self._move_active_selection(-1)
        if code in ("P", "M"):
            return self._move_active_selection(1)
        return False

    def _move_active_selection(self, delta: int) -> bool:
        if self.active_view == "menu":
            self.menu.move(delta)
            return True
        if self.active_view == "list_definitions":
            self.definition_list.move(delta)
            return True
        return False

    def handle_char(self, key: str) -> bool:
        if self.active_view == "create_account":
            return self.create_account.handle_char(key)
        if self.active_view == "add_definition":
            return self.add_definition.handle_char(key)
        return False

    def handle_enter(self) -> bool:
        if self.active_view == "menu":
            return self._activate_menu_selection()
        if self.active_view == "create_account":
            self.create_account.handle_enter(self._submit_account)
            return False
        if self.active_view == "add_definition":
            self.add_definition.handle_enter(self._submit_definition)
            return False
        if self.active_view == "list_definitions":
            self.definition_list.handle_enter(self.node)
            return False
        if self.active_view == "list_accounts":
            return False
        if self.active_view == "settings":
            return False
        return False

    def _activate_menu_selection(self) -> bool:
        label = self.menu.current()
        if label is None:
            return False
        normalized = label.lower()
        if normalized == "quit":
            return True
        if normalized == "create account":
            self.switch_view("create_account")
            return False
        if normalized == "list accounts":
            self.switch_view("list_accounts")
            return False
        if normalized == "list definitions":
            self.switch_view("list_definitions")
            return False
        if normalized == "add a definition":
            self.switch_view("add_definition")
            return False
        if normalized == "settings":
            self.switch_view("settings")
            return False
        # Placeholder for other menu actions.
        return False

    def _submit_account(self, name: str) -> tuple[bool, str]:
        success, message = create_account(self.data_dir, name)
        if success:
            self.list_accounts.refresh(self.data_dir)
            self.switch_view("list_accounts")
        return success, message

    def _submit_definition(self, name: str, expression: str) -> tuple[bool, str]:
        return save_definition(self.data_dir, name, expression)

    def handle_escape(self) -> bool:
        if self.active_view == "menu":
            return True
        self.switch_view("menu")
        return False

    def render(self, refresh: bool = False) -> None:
        lines: List[str] = []
        lines.extend(self.header_block)
        self.header_lines = (0, len(self.header_block) - 1) if self.header_block else None
        if self.header_block:
            lines.append("")
        body_start = len(lines)
        body_lines = self._render_body_lines()
        lines.extend(body_lines)
        if body_lines:
            self.body_lines = (body_start, body_start + len(body_lines) - 1)
        else:
            self.body_lines = None
        lines.append("")
        footer_start = len(lines)
        lines.append(self.footer_text)
        self.footer_lines = (footer_start, footer_start)
        self.lines = lines
        output = "".join(f"{line}\n" for line in lines)
        if refresh:
            sys.stdout.buffer.write(b"\x1b[2J\x1b[H")
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.flush()

    def _render_body_lines(self) -> List[str]:
        if self.active_view == "menu":
            return self.menu.render_lines()
        if self.active_view == "create_account":
            return self.create_account.render_lines()
        if self.active_view == "list_accounts":
            return self.list_accounts.render_lines()
        if self.active_view == "list_definitions":
            return self.definition_list.render_lines()
        if self.active_view == "add_definition":
            return self.add_definition.render_lines()
        if self.active_view == "settings":
            return self.settings_page.render_lines()
        return []


def main() -> int:
    app = App()
    app.render()
    try:
        while True:
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                extended = msvcrt.getwch()
                if app.handle_special_key(extended):
                    app.render(refresh=True)
                continue
            if key == "\t":
                app.advance_selection()
                app.render(refresh=True)
            elif key in ("\r", "\n"):
                if app.handle_enter():
                    break
                app.render(refresh=True)
            elif key == "\x1b":
                if app.handle_escape():
                    break
                app.render(refresh=True)
            else:
                if app.handle_char(key):
                    app.render(refresh=True)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
