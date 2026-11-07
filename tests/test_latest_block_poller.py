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

from utils import latest_block as poller

HASH_A = b"\xaa" * 32
HASH_B = b"\xbb" * 32

FETCH = "astreum.consensus.block.encoding.decode.get_block_from_storage"
HOLDER = "astreum.consensus.block.holders.block_holder"


def make_node(latest_block_hash=None, latest_block=None):
    return SimpleNamespace(
        latest_block_hash=latest_block_hash,
        latest_block=latest_block,
        latest_block_lock=threading.RLock(),
        logger=mock.Mock(),
    )


def block(expr_id):
    return SimpleNamespace(expr_id=expr_id, height=1)


def wait_for(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


class PollerThreadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        for target in (
            "utils.latest_block.persist_node_latest_block_hash",
            "utils.latest_block.persist_node_forks",
            HOLDER,
        ):
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def start(self, node):
        stop = poller.start_latest_block_hash_poller(
            node=node, data_dir=Path(self._tmp.name), poll_interval=0.05
        )
        self.addCleanup(stop)

    def test_failed_fetch_keeps_the_previous_block(self):
        old = block(HASH_A)
        node = make_node(latest_block_hash=HASH_B, latest_block=old)
        with mock.patch(FETCH, side_effect=ValueError("no header")) as fetch:
            self.start(node)
            self.assertTrue(wait_for(lambda: fetch.call_count >= 2))
        self.assertIs(node.latest_block, old)

    def test_loaded_block_is_not_fetched_again(self):
        node = make_node(latest_block_hash=HASH_A, latest_block=block(HASH_A))
        with mock.patch(FETCH) as fetch:
            self.start(node)
            time.sleep(0.3)
        fetch.assert_not_called()

    def test_new_hash_loads_the_new_block(self):
        fetched = block(HASH_B)
        node = make_node(latest_block_hash=HASH_B, latest_block=None)
        with mock.patch(FETCH, return_value=fetched):
            self.start(node)
            self.assertTrue(wait_for(lambda: node.latest_block is fetched))

    def test_no_hash_leaves_no_block(self):
        node = make_node(latest_block_hash=None, latest_block=None)
        with mock.patch(FETCH) as fetch:
            self.start(node)
            time.sleep(0.2)
        fetch.assert_not_called()
        self.assertIsNone(node.latest_block)


class RefreshLatestBlockTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch(HOLDER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_failed_fetch_is_tried_again_for_the_same_hash(self):
        node = make_node(latest_block_hash=HASH_A, latest_block=None)
        fetched = block(HASH_A)
        with mock.patch(FETCH, side_effect=[ValueError("lost"), fetched]) as fetch:
            self.assertFalse(poller._refresh_latest_block(node, HASH_A))
            self.assertIsNone(node.latest_block)
            self.assertTrue(poller._refresh_latest_block(node, HASH_A))
        self.assertEqual(fetch.call_count, 2)
        self.assertIs(node.latest_block, fetched)

    def test_block_for_an_old_hash_is_dropped_when_the_hash_moves_during_the_fetch(self):
        node = make_node(latest_block_hash=HASH_A, latest_block=None)

        def fetch_while_hash_moves(*args, **kwargs):
            with node.latest_block_lock:
                node.latest_block_hash = HASH_B
                node.latest_block = None
            return block(HASH_A)

        with mock.patch(FETCH, side_effect=fetch_while_hash_moves):
            self.assertFalse(poller._refresh_latest_block(node, HASH_A))
        self.assertIsNone(node.latest_block)
        self.assertEqual(node.latest_block_hash, HASH_B)


if __name__ == "__main__":
    unittest.main()
