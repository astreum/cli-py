"""Astreum CLI entry point using Rich for rendering and prompt_toolkit for input."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.text import Text

from accounts import create_account, load_accounts

APP_NAME = "cli-py"
ORG_NAME = "Astreum"

HEADER_ART = r"""
 █████╗   █████╗  ████████╗ ██████╗  ███████╗ ██╗   ██╗ ███╗   ███╗
██╔══██╗ ██╔═══╝  ╚══██╔══╝ ██╔══██╗ ██╔════╝ ██║   ██║ ████╗ ████║
███████║ ╚█████╗     ██║    ██████╔╝ █████╗   ██║   ██║ ██╔████╔██║
██╔══██║  ╚═══██╗    ██║    ██╔══██╗ ██╔══╝   ██║   ██║ ██║╚██╔╝██║
██║  ██║ ██████╔╝    ██║    ██║  ██║ ███████╗ ╚██████╔╝ ██║ ╚═╝ ██║
╚═╝  ╚═╝ ╚═════╝     ╚═╝    ╚═╝  ╚═╝ ╚══════╝  ╚═════╝  ╚═╝     ╚═╝

 ██████╗  ██╗      ██╗
██╔════╝  ██║      ██║
██║       ██║      ██║
██║       ██║      ██║
╚██████╗  ███████╗ ██║
 ╚═════╝  ╚══════╝ ╚═╝
"""


def render_prompt_separator(console: Console) -> None:
    """Draw a simple white line above the prompt."""
    width = console.width
    console.print(Text("─" * max(1, width), style="white"))


def ensure_data_dir() -> Path:
    """Ensure the per-user data directory exists and return its path."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / ORG_NAME / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    # Provision sub-directories that the CLI expects to exist.
    for folder in ("accounts", "definitions", "atoms"):
        (target / folder).mkdir(exist_ok=True)
    settings_path = target / "settings.json"
    if not settings_path.exists():
        settings_path.write_text("{}\n", encoding="utf-8")
    return target


@dataclass
class MenuItem:
    """Representation of a menu entry."""

    label: str
    key: str


MENU_ITEMS = [
    MenuItem("Search", "search"),
    MenuItem("Accounts", "accounts"),
    MenuItem("Create Transaction", "create_transaction"),
    MenuItem("Definitions", "definitions"),
    MenuItem("Terminal", "terminal"),
    MenuItem("Settings", "settings"),
    MenuItem("Quit", "quit"),
]

PLACEHOLDER_DESCRIPTIONS = {
    "search": (
        "Enter a search term and press Enter. The full search experience is coming soon."
    ),
    "definitions": (
        "Manage API definitions and schemas. This view will be available soon."
    ),
    "terminal": (
        "Type a command and press Enter to run it. The integrated terminal is in development."
    ),
}

INTERACTIVE_VIEWS = {"search", "accounts", "terminal"}


def render_header(data_dir: Path) -> Text:
    """Render the header block with ASCII art and metadata."""
    header = Text()
    header.append(HEADER_ART + "\n", style="bold cyan")
    header.append("(c) Astreum Foundation\n", style="dim")
    return header


def render_menu(selected_index: int) -> Text:
    """Render the menu with the current selection highlighted."""
    lines = []
    for index, item in enumerate(MENU_ITEMS):
        prefix = "> " if index == selected_index else "  "
        style = "bold white on blue" if index == selected_index else "white"
        lines.append(Text(prefix + item.label, style=style))
    return Text("\n").join(lines)


def render_view(
    key: str,
    data_dir: Optional[Path] = None,
    accounts_message: Optional[tuple[str, str]] = None,
    pending_account_name: Optional[str] = None,
) -> Text:
    """Render the active view text."""
    if key == "menu":
        body = Text(
            "Use arrow keys (↑/↓ or j/k) or numbers to choose an option.\n", style="dim"
        )
        body.append("Press Enter to open; Esc to return; 'q' to quit.", style="dim")
        return body
    if key == "settings":
        body = Text()
        body.append("Settings\n", style="bold")
        if data_dir is not None:
            body.append(f"Data directory: {data_dir}\n\n", style="green")
        body.append("[ Start API ] (coming soon)\n\n", style="yellow")
        body.append("Press Esc to return to the menu.", style="dim")
        return body
    if key == "accounts":
        body = Text()
        body.append("Accounts\n", style="bold")
        body.append("\n")
        if accounts_message:
            message_text, message_style = accounts_message
            body.append(f"{message_text}\n\n", style=message_style)
        accounts = load_accounts(data_dir)
        if accounts:
            for name, short_hex in accounts:
                body.append(f"{name} - 0x{short_hex}\n", style="white")
        else:
            body.append("No accounts found.\n", style="yellow")
        return body

    title = next((item.label for item in MENU_ITEMS if item.key == key), key.title())
    body = Text()
    body.append(f"{title}\n", style="bold")
    message = PLACEHOLDER_DESCRIPTIONS.get(key, "Coming soon...")
    body.append(f"{message}\n\n", style="yellow")
    body.append("Press Esc to return to the menu.", style="dim")
    return body


def draw(
    console: Console,
    data_dir: Path,
    selected: int,
    active_key: str,
    accounts_message: Optional[tuple[str, str]] = None,
    pending_account_name: Optional[str] = None,
) -> None:
    """Draw the full screen."""
    console.clear()
    console.print(render_header(data_dir))
    console.print()
    if active_key == "menu":
        console.print(render_menu(selected))
        console.print()
        console.print(render_view("menu", data_dir))
    else:
        message = accounts_message if active_key == "accounts" else None
        pending_name = pending_account_name if active_key == "accounts" else None
        console.print(render_view(active_key, data_dir, message, pending_name))


def build_key_bindings(control: Dict[str, Optional[str]]) -> KeyBindings:
    """Create key bindings that update control['action'] and close the prompt."""
    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event) -> None:
        control["action"] = "up"
        event.app.current_buffer.reset()
        event.app.exit("")

    @kb.add("down")
    @kb.add("j")
    def _(event) -> None:
        control["action"] = "down"
        event.app.current_buffer.reset()
        event.app.exit("")

    @kb.add("enter")
    def _(event) -> None:
        text = event.app.current_buffer.text
        if text.strip():
            event.app.exit(text)
        else:
            control["action"] = "open"
            event.app.current_buffer.reset()
            event.app.exit("")

    @kb.add("escape")
    @kb.add("left")
    def _(event) -> None:
        control["action"] = "menu"
        event.app.current_buffer.reset()
        event.app.exit("")

    @kb.add("c-c")
    def _(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    @kb.add("c-d")
    def _(event) -> None:
        event.app.exit(exception=EOFError())

    return kb


def run_cli() -> int:
    """Run the Rich-based CLI loop with prompt_toolkit input handling."""
    data_dir = ensure_data_dir()
    console = Console()

    selected_index = 0
    active_key = "menu"
    pending_account_name: Optional[str] = None
    accounts_message: Optional[tuple[str, str]] = None

    control: Dict[str, Optional[str]] = {"action": None}
    session = PromptSession(key_bindings=build_key_bindings(control))

    while True:
        draw(
            console,
            data_dir,
            selected_index,
            active_key,
            accounts_message,
            pending_account_name,
        )
        control["action"] = None
        should_prompt = active_key in INTERACTIVE_VIEWS
        prompt_message = ""
        placeholder_text = ""
        if should_prompt:
            if active_key == "accounts":
                if pending_account_name is None:
                    prompt_message = "> "
                    placeholder_text = "Enter an account name and press enter to create"
                else:
                    prompt_message = (
                        f"> Create an account called {pending_account_name} (yes/no) "
                    )
            else:
                prompt_message = "> "
        if should_prompt:
            render_prompt_separator(console)
        try:
            with patch_stdout():
                raw = session.prompt(prompt_message, placeholder=placeholder_text)
        except KeyboardInterrupt:
            console.print("\n[red]Interrupted. Goodbye![/red]")
            return 0
        except EOFError:
            console.print("\n[red]EOF received. Goodbye![/red]")
            return 0

        action = control["action"]
        text_input = raw.strip()

        if action:
            lower_action = action.lower()
            if lower_action == "up":
                selected_index = (selected_index - 1) % len(MENU_ITEMS)
                active_key = "menu"
                pending_account_name = None
                accounts_message = None
                continue
            if lower_action == "down":
                selected_index = (selected_index + 1) % len(MENU_ITEMS)
                active_key = "menu"
                pending_account_name = None
                accounts_message = None
                continue
            if lower_action == "menu":
                active_key = "menu"
                pending_account_name = None
                accounts_message = None
                continue
            if lower_action == "open":
                item = MENU_ITEMS[selected_index]
                if item.key == "quit":
                    console.print("[green]Goodbye![/green]")
                    return 0
                active_key = item.key
                pending_account_name = None
                accounts_message = None
                continue

        if not text_input:
            if active_key == "accounts":
                continue
            continue

        if active_key == "accounts":
            if pending_account_name is None:
                lower_accounts = text_input.lower()
                if lower_accounts in {"menu", "m"}:
                    active_key = "menu"
                    pending_account_name = None
                    accounts_message = None
                    continue
                if lower_accounts in {"q", "quit", "exit"}:
                    console.print("[green]Goodbye![/green]")
                    return 0
                if lower_accounts.isdigit():
                    index = int(lower_accounts) - 1
                    if 0 <= index < len(MENU_ITEMS):
                        selected_index = index
                        active_key = "menu"
                        pending_account_name = None
                        accounts_message = None
                        continue
                pending_account_name = text_input
                accounts_message = None
                continue

            response = text_input.lower()
            if response in {"yes", "y"}:
                if data_dir is not None:
                    success, message = create_account(data_dir, pending_account_name)
                    accounts_message = (message, "green" if success else "red")
                else:
                    accounts_message = ("Data directory unavailable.", "red")
                pending_account_name = None
                continue

            if response in {"no", "n"}:
                accounts_message = ("Account creation cancelled.", "yellow")
                pending_account_name = None
                continue

            accounts_message = ("Please answer 'yes' or 'no'.", "red")
            continue

        lower = text_input.lower()
        if lower in {"q", "quit", "exit"}:
            console.print("[green]Goodbye![/green]")
            return 0

        if lower == "up":
            selected_index = (selected_index - 1) % len(MENU_ITEMS)
            active_key = "menu"
            pending_account_name = None
            accounts_message = None
            continue

        if lower == "down":
            selected_index = (selected_index + 1) % len(MENU_ITEMS)
            active_key = "menu"
            pending_account_name = None
            accounts_message = None
            continue

        if lower in {"menu", "m"}:
            active_key = "menu"
            pending_account_name = None
            accounts_message = None
            continue

        if lower in {"open"}:
            item = MENU_ITEMS[selected_index]
            if item.key == "quit":
                console.print("[green]Goodbye![/green]")
                return 0
            active_key = item.key
            pending_account_name = None
            accounts_message = None
            continue

        if lower.isdigit():
            index = int(lower) - 1
            if 0 <= index < len(MENU_ITEMS):
                selected_index = index
                active_key = "menu"
                pending_account_name = None
                accounts_message = None
                continue

        matching_index = next(
            (idx for idx, item in enumerate(MENU_ITEMS) if item.key == lower), None
        )
        if matching_index is not None:
            selected_index = matching_index
            if lower == "quit":
                console.print("[green]Goodbye![/green]")
                return 0
            active_key = lower
            pending_account_name = None
            accounts_message = None
            continue

        console.print(
            "[red]Unknown command. Use arrows, numbers, Enter, Esc, or 'q'.[/red]"
        )


def main() -> int:
    """CLI entry point."""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
