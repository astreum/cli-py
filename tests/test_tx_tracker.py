import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astreum.consensus.models.receipt import STATUS_FAILED, STATUS_SUCCESS, Receipt
from astreum.consensus.transaction import TransactionCode

from utils.tx_tracker import (
    MAX_CHECKS_PER_PASS,
    SENT_FILE_NAME,
    TRACKED_FILE_NAME,
    ClaimStats,
    TransactionTracker,
    start_transaction_tracker,
)

KEY = bytes(range(32))
OTHER = bytes(range(1, 33))
CLAIM = int(TransactionCode.STORAGE_PAYMENT)
TRANSFER = int(TransactionCode.TRANSFER)
SENT_HEADER = "tx_hash,sender,recipient,code,sent_height,sent_time"
TRACKED_HEADER = (
    "tx_hash,sender,recipient,code,sent_height,result,block_hash,"
    "transaction_fee,data_fee,storage_fee,mint"
)
BLOCK_HASH = bytes([0xBB]) * 32


def tx_hash(n):
    return n.to_bytes(32, "big")


def sent_line(n, *, sender=KEY, code=CLAIM, sent_height=5):
    recipient = bytes(32)
    return f"{tx_hash(n).hex()},{sender.hex()},{recipient.hex()},{code},{sent_height},1700000000\n"


def receipt(n, *, status=STATUS_SUCCESS, mint=100):
    return Receipt(
        tx_hash(n),
        transaction_fee=1,
        storage_fee=3,
        data_fee=2,
        execution_fee=0,
        status=status,
        mint=mint,
    )


class TrackerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.sent_path = self.data_dir / SENT_FILE_NAME
        self.tracked_path = self.data_dir / TRACKED_FILE_NAME
        self.node = SimpleNamespace(
            latest_block=SimpleNamespace(height=15),
            config=SimpleNamespace(storage_claim_fee_window=10),
            storage_public_key_bytes=KEY,
            logger=mock.Mock(),
        )
        find = mock.patch("utils.tx_tracker.find_transactions")
        self.find = find.start()
        self.addCleanup(find.stop)
        self.find.return_value = [SimpleNamespace(block_hash=BLOCK_HASH)]
        get = mock.patch("utils.tx_tracker.get_receipt")
        self.get_receipt = get.start()
        self.addCleanup(get.stop)
        self.get_receipt.side_effect = lambda node, block_hash, h: receipt(
            int.from_bytes(h, "big")
        )
        reach = mock.patch(
            "utils.tx_tracker.find_block_by_height", return_value=SimpleNamespace(height=5)
        )
        self.find_block = reach.start()
        self.addCleanup(reach.stop)

    def write_sent(self, *lines, header=True):
        text = (SENT_HEADER + "\n" if header else "") + "".join(lines)
        self.sent_path.write_text(text, encoding="utf-8", newline="")

    def append_sent(self, text):
        with open(self.sent_path, "a", encoding="utf-8", newline="") as f:
            f.write(text)

    def tracked_lines(self):
        return self.tracked_path.read_text(encoding="utf-8").splitlines()

    def tracker(self):
        return TransactionTracker(self.node, self.data_dir)


class CheckDueTests(TrackerTestCase):
    def test_not_due_is_not_checked(self):
        self.node.latest_block.height = 14
        self.write_sent(sent_line(1, sent_height=5))
        self.assertEqual(self.tracker().check_due(), 0)
        self.find.assert_not_called()

    def test_due_row_calls_find_once_with_window(self):
        self.write_sent(sent_line(1, sent_height=5))
        self.tracker().check_due()
        self.find.assert_called_once_with(
            self.node, tx_hash=tx_hash(1), start_height=15, end_height=5, limit=1
        )

    def test_success_writes_row_and_counts(self):
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        lines = self.tracked_lines()
        self.assertEqual(lines[0], TRACKED_HEADER)
        self.assertEqual(
            lines[-1],
            f"{tx_hash(1).hex()},{KEY.hex()},{bytes(32).hex()},{CLAIM},5,"
            f"success,{BLOCK_HASH.hex()},1,2,3,100",
        )
        self.get_receipt.assert_called_once_with(self.node, BLOCK_HASH, tx_hash(1))
        stats = tracker.stats()
        self.assertEqual(
            (stats.sent, stats.succeeded, stats.earned, stats.fees, stats.net, stats.waiting),
            (1, 1, 100, 6, 94, 0),
        )

    def test_failed_receipt_counts_failed(self):
        self.get_receipt.side_effect = None
        self.get_receipt.return_value = receipt(1, status=STATUS_FAILED, mint=0)
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        self.assertIn(",failed,", self.tracked_lines()[-1])
        stats = tracker.stats()
        self.assertEqual((stats.failed, stats.succeeded, stats.earned, stats.fees), (1, 0, 0, 6))
        self.assertEqual(stats.net, -6)

    def test_not_found_counts_not_included(self):
        self.find.return_value = []
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        self.assertTrue(self.tracked_lines()[-1].endswith(",5,not_included,,0,0,0,0"))
        self.get_receipt.assert_not_called()
        stats = tracker.stats()
        self.assertEqual((stats.not_included, stats.fees, stats.waiting), (1, 0, 0))

    def test_receipt_none_retries_next_pass(self):
        self.get_receipt.side_effect = None
        self.get_receipt.return_value = None
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.assertFalse(self.tracked_path.exists())
        self.assertEqual(tracker.stats().waiting, 1)
        self.get_receipt.return_value = receipt(1)
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats().succeeded, 1)

    def test_lookup_error_retries(self):
        self.find.side_effect = ValueError("block not found")
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.node.logger.warning.assert_called()
        self.find.side_effect = None
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(len(self.tracked_lines()), 2)

    def test_restart_does_not_count_twice(self):
        self.write_sent(sent_line(1))
        first = self.tracker()
        first.check_due()
        before = first.stats()
        self.find.reset_mock()
        second = self.tracker()
        self.assertEqual(second.stats(), before)
        self.assertEqual(second.check_due(), 0)
        self.find.assert_not_called()
        self.assertEqual(len(self.tracked_lines()), 2)

    def test_partial_last_line_waits(self):
        line = sent_line(1)
        self.write_sent(line[:40])
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.assertEqual(tracker.stats().sent, 0)
        self.node.logger.warning.assert_not_called()
        self.append_sent(line[40:])
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats().sent, 1)

    def test_duplicate_sent_row_counts_once(self):
        self.write_sent(sent_line(1), sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.stats().sent, 1)
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(self.find.call_count, 1)

    def test_non_claim_row_is_tracked_not_counted(self):
        self.write_sent(sent_line(1, code=TRANSFER))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(len(self.tracked_lines()), 2)
        self.assertEqual(tracker.stats(), ClaimStats())

    def test_other_sender_is_not_counted(self):
        self.write_sent(sent_line(1, sender=OTHER))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats(), ClaimStats())

    def test_max_checks_per_pass(self):
        self.assertEqual(MAX_CHECKS_PER_PASS, 50)
        self.write_sent(*(sent_line(n) for n in range(1, 61)))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 50)
        self.assertEqual(tracker.check_due(), 10)
        self.assertEqual(tracker.stats().succeeded, 60)

    def test_stop_event_ends_pass_early(self):
        self.write_sent(sent_line(1))
        stop = threading.Event()
        stop.set()
        self.assertEqual(self.tracker().check_due(stop), 0)
        self.find.assert_not_called()

    def test_tracked_write_error_retries(self):
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.tracked_path.mkdir()
        self.assertEqual(tracker.check_due(), 0)
        self.node.logger.warning.assert_called()
        self.assertEqual(tracker.stats().waiting, 1)
        self.tracked_path.rmdir()
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats().succeeded, 1)

    def test_no_latest_block_returns_zero(self):
        self.node.latest_block = None
        self.write_sent(sent_line(1))
        self.assertEqual(self.tracker().check_due(), 0)
        self.find.assert_not_called()

    def test_malformed_row_is_skipped(self):
        self.write_sent("a,b,c\n", sent_line(1))
        tracker = self.tracker()
        self.node.logger.warning.assert_called()
        self.assertEqual(tracker.stats().sent, 1)
        self.assertEqual(tracker.check_due(), 1)

    def test_missing_sent_file_is_empty(self):
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.assertEqual(tracker.stats().sent, 0)

    def test_new_sent_lines_are_read_on_the_next_pass(self):
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 1)
        self.append_sent(sent_line(2))
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats().sent, 2)

    def test_partial_tracked_line_after_crash_is_not_glued(self):
        self.write_sent(sent_line(1), sent_line(2))
        self.tracked_path.write_text(
            TRACKED_HEADER + "\n" + tx_hash(1).hex()[:20], encoding="utf-8", newline=""
        )
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 2)
        restarted = self.tracker()
        self.assertEqual(restarted.stats().succeeded, 2)
        self.assertEqual(restarted.check_due(), 0)

    def test_claim_key_from_node_config(self):
        del self.node.storage_public_key_bytes
        self.node.config.storage_public_key_bytes = KEY
        self.write_sent(sent_line(1))
        tracker = self.tracker()
        self.assertEqual(tracker.stats().sent, 1)
        tracker.check_due()
        self.assertEqual(tracker.stats().succeeded, 1)

    def test_failing_rows_do_not_block_later_rows(self):
        def get(node, block_hash, h):
            n = int.from_bytes(h, "big")
            return None if n <= MAX_CHECKS_PER_PASS else receipt(n)

        self.get_receipt.side_effect = get
        self.write_sent(*(sent_line(n) for n in range(1, 61)))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.assertEqual(tracker.check_due(), 10)

    def test_not_found_with_unreachable_range_retries(self):
        self.find.return_value = []
        self.find_block.return_value = None
        self.write_sent(sent_line(1, sent_height=5))
        tracker = self.tracker()
        self.assertEqual(tracker.check_due(), 0)
        self.assertFalse(self.tracked_path.exists())
        self.node.logger.warning.assert_called()
        self.find_block.assert_called_once_with(
            self.node, starting_block=self.node.latest_block, target_height=5
        )
        self.find_block.return_value = SimpleNamespace(height=5)
        self.assertEqual(tracker.check_due(), 1)
        self.assertEqual(tracker.stats().not_included, 1)

    def test_found_does_not_check_range(self):
        self.write_sent(sent_line(1))
        self.tracker().check_due()
        self.find_block.assert_not_called()


class ClaimStatsTests(unittest.TestCase):
    def test_waiting_and_net(self):
        stats = ClaimStats(sent=10, succeeded=6, failed=1, not_included=2, earned=1000, fees=100)
        self.assertEqual(stats.waiting, 1)
        self.assertEqual(stats.net, 900)


class TrackerThreadTests(TrackerTestCase):
    def wait_for(self, condition, timeout=2.0):
        done = threading.Event()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not condition():
            done.wait(0.01)
        return condition()

    def test_thread_runs_and_stops(self):
        with mock.patch.object(TransactionTracker, "check_due", return_value=0) as check:
            tracker, stop = start_transaction_tracker(
                node=self.node, data_dir=self.data_dir, poll_interval=0.01
            )
            self.assertIsInstance(tracker, TransactionTracker)
            self.assertTrue(self.wait_for(lambda: check.call_count >= 1))
            stop()
        self.assertFalse(any(t.name == "tx-tracker" for t in threading.enumerate()))

    def test_pass_error_does_not_stop_thread(self):
        with mock.patch.object(
            TransactionTracker, "check_due", side_effect=[RuntimeError("boom")] + [0] * 1000
        ) as check:
            _, stop = start_transaction_tracker(
                node=self.node, data_dir=self.data_dir, poll_interval=0.01
            )
            try:
                self.assertTrue(self.wait_for(lambda: check.call_count >= 2))
            finally:
                stop()
        self.node.logger.warning.assert_called()

    def test_start_error_raises(self):
        self.tracked_path.mkdir()
        with self.assertRaises(OSError):
            start_transaction_tracker(node=self.node, data_dir=self.data_dir, poll_interval=0.01)
        self.assertFalse(any(t.name == "tx-tracker" for t in threading.enumerate()))

    def test_stop_does_not_wait_for_a_long_check(self):
        release = threading.Event()
        started = threading.Event()

        def long_check(stop_event=None):
            started.set()
            release.wait(5)
            return 0

        with mock.patch.object(TransactionTracker, "check_due", side_effect=long_check), \
                mock.patch("utils.tx_tracker.STOP_TIMEOUT", 0.1):
            _, stop = start_transaction_tracker(
                node=self.node, data_dir=self.data_dir, poll_interval=10.0
            )
            self.assertTrue(started.wait(2))
            began = time.monotonic()
            stop()
            elapsed = time.monotonic() - began
            release.set()
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
