"""GET /list/{root_id} endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .deps import require_node, serialize_atom

router = APIRouter()


@router.get("/list/{root_id}")
def get_atom_list(root_id: str, node=Depends(require_node)):
    """Return an atom chain following next_id pointers from the head atom."""
    try:
        root_bytes = bytes.fromhex(root_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex list root id")

    atoms: Optional[list] = node.get_atom_list(root_bytes)
    if atoms is None:
        raise HTTPException(status_code=404, detail="Atom list not found")

    return [serialize_atom(a) for a in atoms]
