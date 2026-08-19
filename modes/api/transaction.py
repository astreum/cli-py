"""Transaction endpoints — GET and POST."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body

from astreum import Transaction, send_transaction, parse, tokenize
from astreum.consensus.transaction import TransactionCode
from astreum.consensus.transaction.from_storage import get_transaction_from_storage
from astreum.expression import NIL

from .deps import require_node, hex_encode

router = APIRouter()


@router.get("/transaction/{tx_id}")
def get_transaction(tx_id: str, node=Depends(require_node)):
    """Return a transaction by its expr hash."""
    try:
        tx_bytes = bytes.fromhex(tx_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hex transaction id")

    try:
        tx = get_transaction_from_storage(node, tx_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "id": hex_encode(tx.expr_id or tx.hash),
        "chain_id": tx.chain_id,
        "amount": tx.amount,
        "code": tx.code.name if hasattr(tx.code, "name") else int(tx.code),
        "counter": tx.counter,
        "cost_limit": tx.cost_limit,
        "data": repr(tx.data),
        "recipient": tx.recipient.hex(),
        "sender": tx.sender.hex(),
        "signature": hex_encode(tx.signature),
        "body_hash": hex_encode(tx.body_hash),
    }


@router.post("/transaction")
def submit_transaction(payload: dict = Body(...), node=Depends(require_node)):
    """Accept, verify, and broadcast a pre-signed transaction to the network."""
    # 1. Parse hex formats
    try:
        sender_bytes = bytes.fromhex(payload["sender"])
        recipient_bytes = bytes.fromhex(payload["recipient"])
        signature_bytes = bytes.fromhex(payload["signature"])
        body_hash_bytes = bytes.fromhex(payload["body_hash"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid hex formatting or missing fields in parameters")

    # 2. Parse transaction code
    try:
        code_enum = TransactionCode[payload["code"].upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid transaction code: {payload.get('code')}")

    # 3. Parse data expression
    try:
        raw_data = payload.get("data", "")
        data_expr = parse(tokenize(raw_data))[0] if raw_data else NIL
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid data expression: {exc}")

    # 4. Reconstruct and verify transaction
    try:
        tx = Transaction(
            chain_id=payload["chain_id"],
            amount=payload["amount"],
            counter=payload["counter"],
            recipient=recipient_bytes,
            sender=sender_bytes,
            cost_limit=payload.get("cost_limit", 0),
            code=code_enum,
            signature=signature_bytes,
            body_hash=body_hash_bytes,
            data=data_expr,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Transaction validation failed: {exc}")

    # 5. Broadcast via core library send_transaction
    try:
        tx_hash = send_transaction(node, tx)
        return {
            "success": True,
            "tx_hash": tx_hash.hex() if isinstance(tx_hash, bytes) else str(tx_hash),
            "message": "Transaction validated and broadcasted successfully.",
        }
    except Exception as exc:
        # Self-validating node: there is no external validator route to
        # broadcast to. Persist the tx locally and enqueue it for the local
        # validation worker to include in the next block.
        try:
            _enqueue_locally(node, tx)
            return {
                "success": True,
                "tx_hash": (tx.expr().hash()).hex(),
                "message": "Transaction validated and enqueued locally (no external validator route).",
            }
        except Exception as local_exc:
            raise HTTPException(
                status_code=500,
                detail=f"Broadcast failed: {exc}; local enqueue failed: {local_exc}",
            )


def _enqueue_locally(node, tx) -> None:
    """Persist a transaction's exprs and submit it to the local validation queue."""
    from astreum.expression import resolve_inner_exprs
    from astreum.storage.put.hot import put_expr_in_hot_storage
    from astreum.storage.put.cold import put_expr_in_cold_storage

    tx_exprs, missed = resolve_inner_exprs(node, tx.expr())
    if missed:
        raise RuntimeError("transaction data unavailable locally")

    for tx_expr in tx_exprs:
        put_expr_in_hot_storage(node, tx_expr)
        put_expr_in_cold_storage(node, tx_expr)

    tx.hash = tx.expr().hash()
    node._validation_transaction_queue.put(tx)
