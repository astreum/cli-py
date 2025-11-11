from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from astreum._node import Expr, Node


@dataclass
class DefinitionEntry:
    """Simple record for stored definition metadata."""

    label: str
    slug: str
    root_hash: bytes
    path: Path


class DefinitionListPage:
    """Interactive list view that expands definitions on demand."""

    def __init__(self) -> None:
        self.entries: List[DefinitionEntry] = []
        self.index: int = -1
        self.expanded_index: Optional[int] = None
        self.expanded_lines: List[str] = []
        self.message: str = ""

    def refresh(self, data_dir: Path) -> None:
        """Load definition names/hash references without parsing the bodies."""
        definitions_dir = data_dir / "definitions"
        entries: List[DefinitionEntry] = []
        if definitions_dir.exists():
            try:
                for child in definitions_dir.iterdir():
                    if not child.is_file() or child.suffix.lower() != ".bin":
                        continue
                    try:
                        root_hash = child.read_bytes()
                    except OSError:
                        continue
                    label = self._format_label(child.stem)
                    entries.append(
                        DefinitionEntry(
                            label=label,
                            slug=child.stem,
                            root_hash=root_hash,
                            path=child,
                        )
                    )
            except OSError as exc:
                self.entries = []
                self.index = -1
                self.expanded_index = None
                self.expanded_lines = []
                self.message = f"\x1b[91mFailed to load definitions: {exc}\x1b[0m"
                return

        entries.sort(key=lambda entry: entry.label.lower())
        self.entries = entries
        self.index = 0 if entries else -1
        self.expanded_index = None
        self.expanded_lines = []
        self.message = (
            "\x1b[90mPress Enter to expand a definition.\x1b[0m"
            if entries
            else "No definitions saved."
        )

    def move(self, delta: int) -> None:
        """Move the selection pointer by delta positions."""
        if not self.entries:
            self.index = -1
            return
        count = len(self.entries)
        self.index = (self.index + delta) % count

    def handle_enter(self, node: Node) -> None:
        """Expand or collapse the selected definition."""
        if not self.entries or self.index < 0:
            return

        if self.expanded_index == self.index:
            self.expanded_index = None
            self.expanded_lines = []
            return

        entry = self.entries[self.index]
        try:
            expr = Expr.from_atoms(node, entry.root_hash)
        except Exception as exc:
            self.message = f"\x1b[91mFailed to decode '{entry.label}': {exc}\x1b[0m"
            self.expanded_index = None
            self.expanded_lines = []
            return

        representation = repr(expr)
        if not representation:
            representation = "(empty expression)"
        self.expanded_index = self.index
        self.expanded_lines = representation.splitlines() or [representation]
        self.message = ""

    def render_lines(self) -> List[str]:
        """Return body lines for the CLI renderer."""
        lines = ["\x1b[1mList definitions\x1b[0m", ""]
        if not self.entries:
            lines.append(self.message or "No definitions saved.")
            return lines

        for idx, entry in enumerate(self.entries):
            prefix = "> " if idx == self.index else "  "
            lines.append(f"{prefix}{entry.label}")
            if idx == self.expanded_index:
                for line in self.expanded_lines:
                    lines.append(f"    {line}")

        if self.message:
            lines.append("")
            lines.append(self.message)
        return lines

    @staticmethod
    def _format_label(slug: str) -> str:
        label = slug.replace("_", " ").strip()
        return label or "(unnamed definition)"
