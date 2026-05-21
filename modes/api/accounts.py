"""Account-related endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from astreum.validation.models.block import Block
from astreum.validation.models.accounts import Accounts
from astreum.storage.models.atom import ZERO32

from .deps import require_node, hex_encode

router = APIRouter()


@router.get("/block/{block_id}/account/{address}")
def get_block_account(block_id: str, address: str, node=Depends(require_node)):
    """Return account state as of a specific block."""
    try:
        block_bytes = bytes.fromhex(block_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex block id")
    try:
        adr_bytes = bytes.fromhex(address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex account address")

    try:
        block = Block.from_storage(node, block_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if block.accounts_hash is None or block.accounts_hash == ZERO32:
        raise HTTPException(status_code=404, detail="Block has no accounts")

    accounts = Accounts(root_hash=block.accounts_hash)
    try:
        account = accounts.get_account(adr_bytes, node)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load account: {exc}")

    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "balance": account.balance,
        "code_hash": account.code_hash.hex(),
        "counter": account.counter,
        "data_hash": account.data_hash.hex(),
        "channels_hash": account.channels_hash.hex(),
        "atom_hash": hex_encode(account.atom_hash),
    }
