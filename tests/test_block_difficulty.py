import unittest
from types import SimpleNamespace

from modes.api.block import _serialize_block
from modes.tui.pages.block_view import BlockSearchPage


def _block():
    return SimpleNamespace(
        expr_id=b"\x01" * 32,
        chain_id=0,
        height=1,
        previous_block_hash=b"\x02" * 32,
        timestamp=10,
        validation_difficulty=7,
        storage_difficulty=3,
        accounts_hash=b"\x03" * 32,
        transactions_hash=b"\x04" * 32,
        receipts_hash=b"\x05" * 32,
        validator_public_key_bytes=b"\x06" * 32,
        nonce=9,
        total_transaction_fee=1,
        total_storage_fee=2,
        cumulative_total_fee=3,
        cumulative_stake=4,
        body_hash=b"\x07" * 32,
        signature=b"\x08" * 64,
        bloom_hash=b"\x09" * 32,
        previous_block=None,
    )


class TestBlockDifficulty(unittest.TestCase):
    def test_the_api_names_the_validation_difficulty(self):
        data = _serialize_block(_block())
        self.assertEqual(data["validation_difficulty"], 7)
        self.assertNotIn("difficulty", data)

    def test_the_tui_shows_the_validation_difficulty(self):
        text = BlockSearchPage()._format_block(_block())
        self.assertIn("Validation Difficulty: 7", text)


if __name__ == "__main__":
    unittest.main()
