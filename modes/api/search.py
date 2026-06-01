"""GET /search — search for transactions via bloom filters."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from astreum.crypto.bloom_search import bloom_search_tx

from .deps import require_node, hex_encode

router = APIRouter()


@router.get("/search")
def search_transactions(
    tx_hash: Optional[str] = None,
    sender: Optional[str] = None,
    receiver: Optional[str] = None,
    key: Optional[str] = None,
    era_start: int = 0,
    era_end: Optional[int] = None,
    node=Depends(require_node),
):
    """Search for transactions matching filter args across eras.

    Args are hex-encoded bytes. At least one of tx_hash, sender, receiver,
    or key must be provided. Returns a list of block hashes where matching
    transactions may exist (bloom filter — false positives possible).
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

    try:
        results = bloom_search_tx(
            astreum_node=node,
            tx_hash=tx_hash_bytes,
            sender=sender_bytes,
            receiver=receiver_bytes,
            key=key_bytes,
            era_start=era_start,
            era_end=era_end,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "results": [hex_encode(h) for h in results],
        "count": len(results),
    }
