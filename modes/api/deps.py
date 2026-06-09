"""Shared state, dependencies, and helpers for API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from astreum.node import Node
from astreum.machine.models.expression import Expr

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
    """Return lowercase hex of *b*, or None if *b* is None."""
    if b is None:
        return None
    return b.hex()


def serialize_expr(expr: Expr) -> dict:
    """Serialize an Expr to a JSON-compatible dict."""
    if isinstance(expr, Expr.Symbol):
        return {"type": "symbol", "value": expr.value}
    if isinstance(expr, Expr.Bytes):
        return {"type": "bytes", "value": expr.value.hex(), "size": expr.size()}
    if isinstance(expr, Expr.Link):
        return {
            "type": "link",
            "head_hash": (expr.head_hash or expr.head.hash()).hex(),
            "tail_hash": (expr.tail_hash or expr.tail.hash()).hex(),
            "size": expr.size(),
        }
    return {"type": "unknown"}
