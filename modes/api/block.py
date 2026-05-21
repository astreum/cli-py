"""GET /block/{block_id} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum.validation.models.block import Block

from .deps import require_node, hex_encode

router = APIRouter()


@router.get("/block/{block_id}")
def get_block(block_id: str, node=Depends(require_node)):
    """Return full block data by its atom hash."""
    try:
        block_bytes = bytes.fromhex(block_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex block id")

    try:
        block = Block.from_storage(node, block_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": hex_encode(block.atom_hash),
        "version": block.version,
        "chain_id": block.chain_id,
        "height": block.height,
        "previous_block_hash": hex_encode(block.previous_block_hash),
        "timestamp": block.timestamp,
        "difficulty": block.difficulty,
        "accounts_hash": hex_encode(block.accounts_hash),
        "transactions_hash": hex_encode(block.transactions_hash),
        "receipts_hash": hex_encode(block.receipts_hash),
        "validator_public_key_bytes": hex_encode(block.validator_public_key_bytes),
        "nonce": block.nonce,
        "total_transaction_fee": block.total_transaction_fee,
        "total_storage_fee": block.total_storage_fee,
        "cumulative_transaction_fee": block.cumulative_transaction_fee,
        "cumulative_storage_fee": block.cumulative_storage_fee,
        "cumulative_stake": block.cumulative_stake,
        "cumulative_burn": block.cumulative_burn,
        "cumulative_mint": block.cumulative_mint,
        "body_hash": hex_encode(block.body_hash),
        "signature": hex_encode(block.signature),
    }
