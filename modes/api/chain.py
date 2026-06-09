"""GET /chain/{chain_id} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum.consensus.block.iaar import calculate_iaar

from .deps import require_node, hex_encode

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

    lb = node.latest_block
    try:
        astreum_rate = calculate_iaar(lb)
    except (ValueError, ZeroDivisionError):
        astreum_rate = None
    return {
        "id": hex_encode(getattr(lb, "expr_id", None)),
        "version": getattr(lb, "version", 1),
        "chain_id": getattr(lb, "chain_id", chain_id),
        "height": getattr(lb, "height", None),
        "previous_block_hash": hex_encode(getattr(lb, "previous_block_hash", None)),
        "timestamp": getattr(lb, "timestamp", None),
        "difficulty": getattr(lb, "difficulty", None),
        "accounts_hash": hex_encode(getattr(lb, "accounts_hash", None)),
        "transactions_hash": hex_encode(getattr(lb, "transactions_hash", None)),
        "receipts_hash": hex_encode(getattr(lb, "receipts_hash", None)),
        "validator_public_key_bytes": hex_encode(getattr(lb, "validator_public_key_bytes", None)),
        "nonce": getattr(lb, "nonce", None),
        "total_transaction_fee": getattr(lb, "total_transaction_fee", None),
        "total_storage_fee": getattr(lb, "total_storage_fee", None),
        "cumulative_stake": getattr(lb, "cumulative_stake", None),
        "astreum_rate": astreum_rate,
    }
