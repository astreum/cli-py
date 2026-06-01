"""GET /search — search for transactions via bloom filters."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from astreum.crypto.bloom_search import bloom_search_tx
from astreum.validation.models.block import Block

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
    block: Optional[str] = None,
    end_block_height: int = 0,
    limit: int = 10,
    node=Depends(require_node),
):
    """Search for transactions matching filter args.

    Walks backward from the given block (or the latest block) looking for
    matching transactions via bloom filters.  Stops at end_block_height
    (default 0 = genesis) or when limit results are found.

    Args are hex-encoded bytes.  At least one of tx_hash, sender, receiver,
    or key must be provided.
    """
    all_args = (tx_hash, sender, receiver, key)
    if not any(all_args):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: tx_hash, sender, receiver, key",
        )

    try:
        tx_hash_bytes = bytes.fromhex(tx_hash) if tx_hash else b""
        sender_bytes = bytes.fromhex(sender) if sender else b""
        receiver_bytes = bytes.fromhex(receiver) if receiver else b""
        key_bytes = bytes.fromhex(key) if key else b""
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex in query parameter")

    # Resolve starting block
    starting_block = None
    if block:
        try:
            block_hash_bytes = bytes.fromhex(block)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex in block parameter")
        try:
            starting_block = Block.from_storage(node, block_hash_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=f"Block not found: {exc}")
    else:
        starting_block = node.latest_block

    if starting_block is None:
        return {"results": [], "count": 0}

    try:
        results = bloom_search_tx(
            astreum_node=node,
            tx_hash=tx_hash_bytes,
            sender=sender_bytes,
            receiver=receiver_bytes,
            key=key_bytes,
            starting_block=starting_block,
            end_block_height=end_block_height,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "results": [_serialize_tx(tx) for tx in results],
        "count": len(results),
    }
