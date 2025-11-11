from pathlib import Path
from typing import List

from accounts import load_accounts


class ListAccountsPage:
    """Read-only list of accounts with their public keys."""

    def __init__(self) -> None:
        self.entries: List[tuple[str, str]] = []

    def refresh(self, data_dir: Path) -> None:
        self.entries = load_accounts(data_dir)

    def render_lines(self) -> List[str]:
        lines = ["\x1b[1mList accounts\x1b[0m", ""]
        if not self.entries:
            lines.append("No accounts found.")
            return lines
        for name, public_hex in self.entries:
            lines.append(f"{name} - 0x{public_hex}")
        return lines
