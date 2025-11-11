"""Definition management helpers for the Astreum CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from astreum._node import Expr, ParseError, parse, tokenize, Atom

@dataclass
class DefinitionFormState:
    """State for the Add Definition interactive view."""

    name: str = ""
    expression: str = ""
    focus: str = "name"
    message: Optional[tuple[str, str]] = None


def _slugify_definition_name(name: str) -> str:
    """Convert a definition name into a filesystem-friendly slug."""
    cleaned = re.sub(r"\s+", "_", name.strip())
    slug = re.sub(r"[^0-9a-zA-Z_-]+", "_", cleaned)
    slug = slug.strip("_")
    if not slug:
        slug = "definition"
    return slug


def save_definition(data_dir: Path, name: str, expression: str) -> tuple[bool, str]:
    """Persist a Lispeum-style definition and its atoms to the data directory."""
    try:
        tokens = tokenize(expression)
    except ParseError as exc:
        return False, f"Failed to tokenize expression: {exc}"
    except Exception as exc:
        return False, f"Unexpected tokenization error: {exc}"

    parse_args = tokens if isinstance(tokens, tuple) else (tokens,)
    try:
        parsed = parse(*parse_args)  # type: ignore[arg-type]
    except ParseError as exc:
        return False, f"Failed to parse expression: {exc}"
    except Exception as exc:
        return False, f"Failed to parse expression: {exc}"

    expr, remaining = _unpack_parse_result(parsed)
    if remaining:
        return False, "Failed to parse expression: unexpected trailing tokens."
    if expr is None:
        return False, "Parser did not return a valid expression."

    try:
        root_atom_bytes, atoms = expr.to_atoms()
    except Exception as exc:
        return False, f"Failed to convert expression: {exc}"

    atoms_dir = data_dir / "atoms"
    definitions_dir = data_dir / "definitions"
    atoms_dir.mkdir(exist_ok=True)
    definitions_dir.mkdir(exist_ok=True)

    saved_atoms = 0
    for atom in atoms:
        if not isinstance(atom, Atom):
            return False, "expr_to_atoms returned an unexpected atom type."
        try:
            atom_bytes = atom.to_bytes()
        except Exception as exc:
            return False, f"Failed to serialise atom: {exc}"
        object_id = atom.object_id()
        object_hex = (
            object_id.hex()
            if isinstance(object_id, (bytes, bytearray))
            else str(object_id)
        )
        atom_path = atoms_dir / f"{object_hex}.bin"
        try:
            atom_path.write_bytes(atom_bytes)
        except OSError as exc:
            return False, f"Failed to write atom {object_hex}: {exc}"
        saved_atoms += 1

    slug = _slugify_definition_name(name)
    definition_path = definitions_dir / f"{slug}.bin"
    suffix = 1
    while definition_path.exists():
        definition_path = definitions_dir / f"{slug}_{suffix}.bin"
        suffix += 1

    try:
        definition_path.write_bytes(root_atom_bytes)
    except OSError as exc:
        return False, f"Failed to save definition '{slug}': {exc}"

    return True, f"Saved definition '{definition_path.stem}'. Wrote {saved_atoms} atoms."


def _unpack_parse_result(
    parsed: Tuple[Expr, List[str]] | Expr,
) -> Tuple[Optional[Expr], List[str]]:
    """Return the parsed expression and any trailing tokens."""

    if isinstance(parsed, tuple):
        expr, remaining = parsed
    else:
        expr, remaining = parsed, []

    if isinstance(expr, (Expr.Symbol, Expr.Bytes, Expr.ListExpr)):
        return expr, remaining
    return None, remaining
