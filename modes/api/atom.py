"""GET /atom/{atom_id} endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from astreum.machine.models.expression import Expr

from .deps import require_node, serialize_expr

router = APIRouter()


@router.get("/atom/{atom_id}")
def get_atom(atom_id: str, node=Depends(require_node)):
    """Return a single atom by its blake3 id (64-char hex)."""
    try:
        atom_id_bytes = bytes.fromhex(atom_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex atom id")

    expr: Optional[Expr] = node.get_expr(atom_id_bytes)
    if expr is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    return serialize_expr(expr)
