"""Block endpoints — by hash and by height."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum.consensus.block.encoding.decode import get_block_from_storage
from astreum.consensus.block.rate import calculate_discount_rate

from .deps import require_node, hex_encode

router = APIRouter()

MAX_CURVE_DURATION = 1 << 40


def _rate_curve(block, node=None) -> list[dict]:
    """Discount rate across windowed durations — the chain's yield curve.

    Duration 0 is the all-time rate; further entries are pow2 block windows
    (1, 2, 4, ...) while statistics for the window are available.
    """
    curve = []
    duration = 0
    while duration <= MAX_CURVE_DURATION:
        try:
            rate = calculate_discount_rate(block, node=node, range_blocks=duration)
        except (ValueError, ZeroDivisionError):
            break
        curve.append({"duration": duration, "rate": rate})
        duration = 1 if duration == 0 else duration * 2
    return curve


def _serialize_block(block, node=None) -> dict:
    rate_curve = _rate_curve(block, node=node)
    astreum_rate = rate_curve[0]["rate"] if rate_curve else None

    return {
        "id": hex_encode(block.expr_id),
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
        "cumulative_total_fee": block.cumulative_total_fee,
        "cumulative_stake": block.cumulative_stake,
        "total_mint": block.total_mint,
        "body_hash": hex_encode(block.body_hash),
        "signature": hex_encode(block.signature),
        "astreum_rate": astreum_rate,
        "rate_curve": rate_curve,
    }


@router.get("/block/{block_id}")
def get_block(block_id: str, node=Depends(require_node)):
    """Return full block data by its expr hash."""
    try:
        block_bytes = bytes.fromhex(block_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex block id")

    try:
        block = get_block_from_storage(node, block_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return _serialize_block(block, node)


@router.get("/block")
def get_block_by_height(height: int, node=Depends(require_node)):
    """Return full block data by chain height."""
    from astreum import get_block as _get_block

    block = _get_block(node, height=height)
    if block is None:
        raise HTTPException(
            status_code=404, detail=f"Block at height {height} not found"
        )

    return _serialize_block(block, node)
