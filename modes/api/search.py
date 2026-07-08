"""GET /search — search for transactions via bloom filters."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from astreum import find_transactions
from astreum.consensus.models.block import Block

from .deps import require_node, hex_encode

router = APIRouter()


def _serialize_tx(tx) -> dict:
    """Serialize a Transaction to a JSON-compatible dict."""
    return {
        "id": hex_encode(tx.atom_hash),
        "block_hash": hex_encode(tx.block_hash),
        "version": tx.version,
        "chain_id": tx.chain_id,
        "amount": tx.amount,
        "code": tx.code.name if hasattr(tx.code, "name") else int(tx.code),
        "counter": tx.counter,
        "cost_limit": tx.cost_limit,
        "data": tx.data.hex(),
        "recipient": tx.recipient.hex(),
        "sender": tx.sender.hex(),
        "signature": hex_encode(tx.signature),
        "body_hash": hex_encode(tx.body_hash),
    }


@router.get("/search")
def search_transactions(
    tx_hash: Optional[str] = None,
    sender: Optional[str] = None,
    receiver: Optional[str] = None,
    key: Optional[str] = None,
    start_block_hash: Optional[str] = None,
    start_block_height: Optional[int] = None,
    end_block_hash: Optional[str] = None,
    end_block_height: int = 0,
    limit: int = 10,
    node=Depends(require_node),
):
    """Search for transactions matching filter args.

    Walks backward from start_height (or the block hash) looking for
    matching transactions via bloom filters.  Stops at end_block_height
    or the end_block hash (default 0 = genesis) or when limit results
    are found.

    Args are hex-encoded bytes.  At least one of tx_hash, sender, receiver,
    or key must be provided.  Provide start_block_hash or start_block_height, not both.
    Provide end_block_hash or end_block_height, not both.
    """
    all_args = (tx_hash, sender, receiver, key)
    if not any(all_args):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: tx_hash, sender, receiver, key",
        )

    if start_block_hash and start_block_height is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide start_block_hash or start_block_height, not both",
        )

    if end_block_hash and end_block_height != 0:
        raise HTTPException(
            status_code=400,
            detail="Provide end_block_hash or end_block_height, not both",
        )

    try:
        tx_hash_bytes = bytes.fromhex(tx_hash) if tx_hash else b""
        sender_bytes = bytes.fromhex(sender) if sender else b""
        receiver_bytes = bytes.fromhex(receiver) if receiver else b""
        key_bytes = bytes.fromhex(key) if key else b""
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex in query parameter")

    # Resolve starting height
    resolved_start_height = start_block_height
    if start_block_hash:
        try:
            block_hash_bytes = bytes.fromhex(start_block_hash)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex in start_block_hash parameter")
        try:
            b = Block.from_storage(node, block_hash_bytes)
            resolved_start_height = b.height
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=f"Start block not found: {exc}")

    # Resolve end height
    resolved_end_height = end_block_height
    if end_block_hash:
        try:
            end_hash_bytes = bytes.fromhex(end_block_hash)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex in end_block_hash parameter")
        try:
            b = Block.from_storage(node, end_hash_bytes)
            resolved_end_height = b.height
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=f"End block not found: {exc}")

    try:
        results = find_transactions(
            node,
            tx_hash=tx_hash_bytes,
            sender=sender_bytes,
            receiver=receiver_bytes,
            key=key_bytes,
            start_height=resolved_start_height,
            end_height=resolved_end_height,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "results": [_serialize_tx(tx) for tx in results],
        "count": len(results),
    }
