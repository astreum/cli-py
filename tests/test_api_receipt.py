import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from astreum.consensus.models.receipt import STATUS_FAILED, STATUS_SUCCESS

from modes.api.receipt import _serialize_receipt, get_block_receipt


def _receipt(status=STATUS_SUCCESS):
    return SimpleNamespace(
        transaction_hash=b"\x22" * 32,
        status=status,
        transaction_fee=1,
        data_fee=2,
        execution_fee=3,
        storage_fee=4,
        mint=5,
        logs_hash=b"\x33" * 32,
    )


class TestSerializeReceipt(unittest.TestCase):
    def test_serialize_success_receipt(self):
        self.assertEqual(
            _serialize_receipt(_receipt(), b"\x11" * 32),
            {
                "transaction_hash": "22" * 32,
                "block_hash": "11" * 32,
                "status": 0,
                "transaction_fee": 1,
                "data_fee": 2,
                "execution_fee": 3,
                "storage_fee": 4,
                "mint": 5,
                "logs_hash": "33" * 32,
            },
        )

    def test_serialize_failed_receipt(self):
        result = _serialize_receipt(_receipt(STATUS_FAILED), b"\x11" * 32)
        self.assertEqual(result["status"], 1)


class TestGetBlockReceipt(unittest.TestCase):
    def test_receipt_found(self):
        node = object()
        with patch("modes.api.receipt.get_receipt", return_value=_receipt()) as get:
            result = get_block_receipt("AB" * 32, "22" * 32, node=node)
        get.assert_called_once_with(node, bytes.fromhex("ab" * 32), bytes.fromhex("22" * 32))
        self.assertEqual(result, _serialize_receipt(_receipt(), b"\xab" * 32))
        self.assertEqual(result["block_hash"], "ab" * 32)

    def test_receipt_none_is_404(self):
        with patch("modes.api.receipt.get_receipt", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                get_block_receipt("11" * 32, "22" * 32, node=object())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Receipt not available")

    def test_value_error_is_404_with_message(self):
        with patch("modes.api.receipt.get_receipt", side_effect=ValueError("block not found")):
            with self.assertRaises(HTTPException) as ctx:
                get_block_receipt("11" * 32, "22" * 32, node=object())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "block not found")

    def test_bad_block_hex_is_400(self):
        with patch("modes.api.receipt.get_receipt") as get:
            with self.assertRaises(HTTPException) as ctx:
                get_block_receipt("zz", "22" * 32, node=object())
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Invalid hex block id")
        get.assert_not_called()

    def test_bad_tx_hex_is_400(self):
        with patch("modes.api.receipt.get_receipt") as get:
            with self.assertRaises(HTTPException) as ctx:
                get_block_receipt("11" * 32, "zz", node=object())
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Invalid hex transaction id")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
