"""GET /block/{block_hash}/receipt/{tx_hash} — receipt of a transaction in a block."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum import get_receipt

from .deps import require_node, hex_encode

router = APIRouter()


def _serialize_receipt(receipt, block_hash: bytes) -> dict:
    return {
        "transaction_hash": hex_encode(receipt.transaction_hash),
        "block_hash": hex_encode(block_hash),
        "status": int(receipt.status),
        "transaction_fee": int(receipt.transaction_fee),
        "data_fee": int(receipt.data_fee),
        "execution_fee": int(receipt.execution_fee),
        "storage_fee": int(receipt.storage_fee),
        "mint": int(receipt.mint),
        "logs_hash": hex_encode(receipt.logs_hash),
    }


@router.get("/block/{block_hash}/receipt/{tx_hash}")
def get_block_receipt(block_hash: str, tx_hash: str, node=Depends(require_node)):
    """Return the receipt of a transaction in a block.

    A 404 means the receipt is not available now. The client can try again later.
    """
    try:
        block_bytes = bytes.fromhex(block_hash)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex block id")
    try:
        tx_bytes = bytes.fromhex(tx_hash)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex transaction id")

    try:
        receipt = get_receipt(node, block_bytes, tx_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not available")

    return _serialize_receipt(receipt, block_bytes)
