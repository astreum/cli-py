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
    return target


@dataclass
class MenuItem:
    """Representation of a menu entry."""

    label: str
    key: str


MENU_ITEMS = [
    MenuItem("Search", "search"),
    MenuItem("Create Account", "create_account"),
    MenuItem("List Accounts", "list_accounts"),
    MenuItem("Create Transaction", "create_transaction"),
    MenuItem("Start API", "start_api"),
    MenuItem("Settings", "settings"),
    MenuItem("Quit", "quit"),
]


def render_header(data_dir: Path) -> Text:
    """Render the header block with ASCII art and metadata."""
    header = Text()
    header.append(HEADER_ART + "\n", style="bold cyan")
    header.append("(c) Astreum Foundation\n", style="dim")
    header.append(f"Data directory: {data_dir}", style="green")
    return header


def render_menu(selected_index: int) -> Text:
    """Render the menu with the current selection highlighted."""
    lines = []
    for index, item in enumerate(MENU_ITEMS):
        prefix = "> " if index == selected_index else "  "
        style = "bold white on blue" if index == selected_index else "white"
        lines.append(Text(prefix + item.label, style=style))
    return Text("\n").join(lines)


def render_view(key: str) -> Text:
    """Render the active view text."""
    if key == "menu":
        body = Text(
            "Use arrow keys (↑/↓ or j/k) or numbers to choose an option.\n", style="dim"
        )
        body.append("Press Enter to open; Esc to return; 'q' to quit.", style="dim")
        return body

    title = next((item.label for item in MENU_ITEMS if item.key == key), key.title())
    body = Text()
    body.append(f"{title}\n", style="bold")
    body.append("Coming soon...\n\n", style="yellow")
    body.append("Press Esc to return to the menu.", style="dim")
    return body


def draw(console: Console, data_dir: Path, selected: int, active_key: str) -> None:
    """Draw the full screen."""
    console.clear()
    console.print(render_header(data_dir))
    console.print()
    if active_key == "menu":
        console.print(render_menu(selected))
        console.print()
        console.print(render_view("menu"))
    else:
        console.print(render_view(active_key))


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

    control: Dict[str, Optional[str]] = {"action": None}
    session = PromptSession(key_bindings=build_key_bindings(control))

    while True:
        draw(console, data_dir, selected_index, active_key)
        control["action"] = None
        render_prompt_separator(console)
        try:
            with patch_stdout():
                raw = session.prompt("> ")
        except KeyboardInterrupt:
            console.print("\n[red]Interrupted. Goodbye![/red]")
            return 0
        except EOFError:
            console.print("\n[red]EOF received. Goodbye![/red]")
            return 0

        command = control["action"] or raw.strip()
        if not command:
            continue

        lower = command.lower()
        if lower in {"q", "quit", "exit"}:
            console.print("[green]Goodbye![/green]")
            return 0

        if lower == "up":
            selected_index = (selected_index - 1) % len(MENU_ITEMS)
            active_key = "menu"
            continue

        if lower == "down":
            selected_index = (selected_index + 1) % len(MENU_ITEMS)
            active_key = "menu"
            continue

        if lower in {"menu", "m"}:
            active_key = "menu"
            continue

        if lower in {"open"}:
            item = MENU_ITEMS[selected_index]
            if item.key == "quit":
                console.print("[green]Goodbye![/green]")
                return 0
            active_key = item.key
            continue

        if lower.isdigit():
            index = int(lower) - 1
            if 0 <= index < len(MENU_ITEMS):
                selected_index = index
                active_key = "menu"
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
            continue

        console.print(
            "[red]Unknown command. Use arrows, numbers, Enter, Esc, or 'q'.[/red]"
        )


def main() -> int:
    """CLI entry point."""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
