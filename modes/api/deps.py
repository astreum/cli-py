"""Shared state, dependencies, and helpers for API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from astreum.node import Node
from astreum.storage.models.atom import Atom, AtomKind, ZERO32

_node: Optional[Node] = None


def set_node(node: Node) -> None:
    """Cache the running Node instance for API endpoint access."""
    global _node
    _node = node


def require_node() -> Node:
    """Dependency: inject the node, raise 503 if not initialized."""
    if _node is None:
        raise HTTPException(status_code=503, detail="Node not initialized")
    return _node


def hex_encode(b: Optional[bytes]) -> Optional[str]:
    """Return lowercase hex of *b*, or None if *b* is None/ZERO32."""
    if b is None or b == ZERO32:
        return None
    return b.hex()


_kind_label = {
    AtomKind.SYMBOL: "symbol",
    AtomKind.BYTES: "bytes",
    AtomKind.LIST: "list",
}


def serialize_atom(atom: Atom) -> dict:
    return {
        "id": atom.object_id().hex(),
        "kind": _kind_label.get(atom.kind, str(atom.kind.value)),
        "data": atom.data.hex(),
        "next_id": atom.next_id.hex(),
        "size": atom.size,
    }
