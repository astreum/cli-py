"""GET /chain/{chain_id} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .deps import require_node
from .block import _serialize_block

router = APIRouter()


@router.get("/chain/{chain_id}")
def get_chain(chain_id: int, node=Depends(require_node)):
    """Return the latest block for *chain_id*, or null if not tracked."""
    node_chain_id = node.config.get("chain_id")
    if chain_id != node_chain_id:
        raise HTTPException(
            status_code=404,
            detail=f"Chain {chain_id} not tracked by this node",
        )

    if node.latest_block is None:
        return None

    return _serialize_block(node.latest_block, node)
