"""GET /list/{root_id} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum.storage.get.list import get_expr_list as _get_expr_list

from .deps import require_node, serialize_expr

router = APIRouter()


@router.get("/list/{root_id}")
def get_expr_list(root_id: str, node=Depends(require_node)):
    """Return the Expr list chain from the given root hash."""
    try:
        root_bytes = bytes.fromhex(root_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex list root id")

    header = _get_expr_list(node, root_bytes)
    if header is None:
        raise HTTPException(status_code=404, detail="Expr list not found")

    from astreum.expression.helpers import resolve_list_exprs

    items, _ = resolve_list_exprs(node, header)
    return [serialize_expr(e) for e in items]
