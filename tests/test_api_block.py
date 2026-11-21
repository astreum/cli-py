import unittest
from types import SimpleNamespace

from astreum.consensus.models.statistics import BlockStatistics

from modes.api.block import _serialize_block
from modes.tui.pages.block_view import BlockSearchPage


def _statistics(**overrides):
    values = dict(
        total_fees=3,
        total_balance=4,
        cumulative_total_balance=5,
        total_claims=6,
        total_tx_fees=7,
        total_tx_bytes=8,
        total_loan_count=9,
        total_loaned=10,
        total_written_off=11,
    )
    values.update(overrides)
    return BlockStatistics(**values)


def _block(*, previous_block=None, statistics=None):
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
        total_base_fee=12,
        total_storage_fee=2,
        transaction_count=13,
        statistics=statistics,
        body_hash=b"\x07" * 32,
        signature=b"\x08" * 64,
        bloom_hash=b"\x09" * 32,
        previous_block=previous_block,
    )


class TestSerializeBlock(unittest.TestCase):
    def test_the_api_names_the_validation_difficulty(self):
        data = _serialize_block(_block())
        self.assertEqual(data["validation_difficulty"], 7)
        self.assertNotIn("difficulty", data)

    def test_the_api_returns_the_counters(self):
        data = _serialize_block(_block())
        self.assertEqual(data["storage_difficulty"], 3)
        self.assertEqual(data["total_base_fee"], 12)
        self.assertEqual(data["transaction_count"], 13)

    def test_the_api_returns_one_statistics_value(self):
        data = _serialize_block(_block(statistics=_statistics()))
        self.assertEqual(data["statistics"]["total_fees"], 3)
        self.assertEqual(data["statistics"]["cumulative_total_balance"], 5)
        self.assertNotIn("cumulative_total_fee", data)
        self.assertNotIn("cumulative_stake", data)
        self.assertNotIn("rate_curve", data)

    def test_the_statistics_are_none_without_a_value(self):
        self.assertIsNone(_serialize_block(_block())["statistics"])

    def test_the_rate_is_the_fee_total_over_the_cumulative_balance(self):
        parent = SimpleNamespace(
            statistics=_statistics(total_fees=101, cumulative_total_balance=100)
        )
        data = _serialize_block(_block(previous_block=parent))
        self.assertEqual(data["astreum_rate"], 101 / 100)

    def test_the_rate_is_none_without_a_parent(self):
        self.assertIsNone(_serialize_block(_block())["astreum_rate"])


class TestBlockPage(unittest.TestCase):
    def test_the_tui_shows_the_validation_difficulty(self):
        text = BlockSearchPage()._format_block(_block())
        self.assertIn("Validation Difficulty: 7", text)

    def test_the_tui_shows_the_statistics(self):
        text = BlockSearchPage()._format_block(_block(statistics=_statistics()))
        self.assertIn("Total Fees:                      3", text)
        self.assertIn("Cumulative Total Balance:        5", text)

    def test_the_tui_says_when_the_statistics_are_missing(self):
        text = BlockSearchPage()._format_block(_block())
        self.assertIn("STATISTICS", text)
        self.assertIn("Not set", text)


if __name__ == "__main__":
    unittest.main()
