"""GET /expr/{expr_id} endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from astreum.expression import Expr
from astreum.storage.get.single import get_expr

from .deps import require_node, serialize_expr

router = APIRouter()


@router.get("/expr/{expr_id}")
def get_expr_endpoint(expr_id: str, node=Depends(require_node)):
    """Return a single expression by its blake3 hash (64-char hex)."""
    try:
        expr_id_bytes = bytes.fromhex(expr_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex expression id")

    expr: Optional[Expr] = get_expr(node, expr_id_bytes)
    if expr is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    return serialize_expr(expr)
