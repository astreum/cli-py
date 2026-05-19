"""Astreum API — FastAPI server exposing node data over HTTP."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from astreum.node import Node
from astreum.storage.models.atom import Atom, AtomKind, ZERO32
from astreum.validation.models.block import Block
from astreum.validation.models.accounts import Accounts
from astreum.consensus.transaction.from_storage import get_transaction_from_storage

logger = logging.getLogger("astreum.api")

# ---------------------------------------------------------------------------
# Shared node reference — set by the mode runner before uvicorn boots
# ---------------------------------------------------------------------------
_node: Optional[Node] = None


def set_node(node: Node) -> None:
    """Cache the running Node instance for API endpoint access."""
    global _node
    _node = node


def _require_node() -> Node:
    """Dependency: inject the node, raise 503 if not initialized."""
    if _node is None:
        raise HTTPException(status_code=503, detail="Node not initialized")
    return _node


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Astreum API",
    description="Read-only HTTP API for the Astreum blockchain platform.",
    version="0.1.0",
)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Helper — safe hex encoding
# ---------------------------------------------------------------------------
def _hex(b: Optional[bytes]) -> Optional[str]:
    """Return lowercase hex of *b*, or None if *b* is None/ZERO32."""
    if b is None or b == ZERO32:
        return None
    return b.hex()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

_kind_label = {AtomKind.SYMBOL: "symbol", AtomKind.BYTES: "bytes", AtomKind.LIST: "list"}


def _serialize_atom(atom: Atom) -> dict:
    return {
        "id": atom.object_id().hex(),
        "kind": _kind_label.get(atom.kind, str(atom.kind.value)),
        "data": atom.data.hex(),
        "next_id": atom.next_id.hex(),
        "size": atom.size,
    }


@app.get("/atom/{atom_id}")
def get_atom(atom_id: str, node: Node = Depends(_require_node)):
    """Return a single atom by its blake3 id (64-char hex)."""
    try:
        atom_id_bytes = bytes.fromhex(atom_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex atom id")

    atom: Optional[Atom] = node.get_atom(atom_id_bytes)
    if atom is None:
        raise HTTPException(status_code=404, detail="Atom not found")

    return _serialize_atom(atom)


@app.get("/list/{root_id}")
def get_atom_list(root_id: str, node: Node = Depends(_require_node)):
    """Return an atom chain following next_id pointers from the head atom."""
    try:
        root_bytes = bytes.fromhex(root_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex list root id")

    atoms: Optional[list] = node.get_atom_list(root_bytes)
    if atoms is None:
        raise HTTPException(status_code=404, detail="Atom list not found")

    return [_serialize_atom(a) for a in atoms]


@app.get("/chain/{chain_id}")
def get_chain(chain_id: int, node: Node = Depends(_require_node)):
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
    return {
        "id": _hex(getattr(lb, "atom_hash", None)),
        "version": getattr(lb, "version", 1),
        "chain_id": getattr(lb, "chain_id", chain_id),
        "height": getattr(lb, "height", None),
        "previous_block_hash": _hex(getattr(lb, "previous_block_hash", None)),
        "timestamp": getattr(lb, "timestamp", None),
        "difficulty": getattr(lb, "difficulty", None),
        "accounts_hash": _hex(getattr(lb, "accounts_hash", None)),
        "transactions_hash": _hex(getattr(lb, "transactions_hash", None)),
        "receipts_hash": _hex(getattr(lb, "receipts_hash", None)),
        "validator_public_key_bytes": _hex(getattr(lb, "validator_public_key_bytes", None)),
        "nonce": getattr(lb, "nonce", None),
        "total_transaction_fee": getattr(lb, "total_transaction_fee", None),
        "total_storage_fee": getattr(lb, "total_storage_fee", None),
        "cumulative_stake": getattr(lb, "cumulative_stake", None),
    }


@app.get("/block/{block_id}")
def get_block(block_id: str, node: Node = Depends(_require_node)):
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
        "id": _hex(block.atom_hash),
        "version": block.version,
        "chain_id": block.chain_id,
        "height": block.height,
        "previous_block_hash": _hex(block.previous_block_hash),
        "timestamp": block.timestamp,
        "difficulty": block.difficulty,
        "accounts_hash": _hex(block.accounts_hash),
        "transactions_hash": _hex(block.transactions_hash),
        "receipts_hash": _hex(block.receipts_hash),
        "validator_public_key_bytes": _hex(block.validator_public_key_bytes),
        "nonce": block.nonce,
        "total_transaction_fee": block.total_transaction_fee,
        "total_storage_fee": block.total_storage_fee,
        "cumulative_transaction_fee": block.cumulative_transaction_fee,
        "cumulative_storage_fee": block.cumulative_storage_fee,
        "cumulative_stake": block.cumulative_stake,
        "cumulative_burn": block.cumulative_burn,
        "cumulative_mint": block.cumulative_mint,
        "body_hash": _hex(block.body_hash),
        "signature": _hex(block.signature),
    }


@app.get("/block/{block_id}/account/{address}")
def get_block_account(block_id: str, address: str, node: Node = Depends(_require_node)):
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
        "atom_hash": _hex(account.atom_hash),
    }


@app.get("/transaction/{tx_id}")
def get_transaction(tx_id: str, node: Node = Depends(_require_node)):
    """Return a transaction by its atom hash."""
    try:
        tx_bytes = bytes.fromhex(tx_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex transaction id")

    try:
        tx = get_transaction_from_storage(node, tx_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": _hex(tx.atom_hash),
        "version": tx.version,
        "chain_id": tx.chain_id,
        "amount": tx.amount,
        "code": tx.code.name if hasattr(tx.code, "name") else int(tx.code),
        "counter": tx.counter,
        "cost_limit": tx.cost_limit,
        "data": tx.data.hex(),
        "recipient": tx.recipient.hex(),
        "sender": tx.sender.hex(),
        "signature": _hex(tx.signature),
        "body_hash": _hex(tx.body_hash),
    }
