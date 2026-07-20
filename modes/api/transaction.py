"""Transaction endpoints — GET and POST."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body

from astreum.consensus.transaction.from_storage import get_transaction_from_storage
from astreum.expression import bytes_

from .deps import require_node, hex_encode

router = APIRouter()


@router.get("/transaction/{tx_id}")
def get_transaction(tx_id: str, node=Depends(require_node)):
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
        "id": hex_encode(tx.expr_id or tx.hash),
        "chain_id": tx.chain_id,
        "amount": tx.amount,
        "code": tx.code.name if hasattr(tx.code, "name") else int(tx.code),
        "counter": tx.counter,
        "cost_limit": tx.cost_limit,
        "data": (tx.data.value.hex() if tx.data is not None and tx.data.base == "bytes" and tx.data.value else ""),
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
        data_bytes = bytes.fromhex(payload.get("data", "")) if payload.get("data") else b""
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid hex formatting or missing fields in parameters")

    # 2. Parse transaction code
    try:
        from astreum.consensus.transaction import TransactionCode
        code_enum = TransactionCode[payload["code"].upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid transaction code: {payload.get('code')}")

    # 3. Reconstruct and verify transaction
    try:
        from astreum.consensus.transaction import Transaction
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
            data=bytes_(data_bytes),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Transaction validation failed: {exc}")

    # 4. Broadcast via core library send_transaction
    try:
        from astreum.consensus.transaction import send_transaction
        tx_hash = send_transaction(node, tx)
        return {
            "success": True,
            "tx_hash": tx_hash.hex() if isinstance(tx_hash, bytes) else str(tx_hash),
            "message": "Transaction validated and broadcasted successfully.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {exc}")
