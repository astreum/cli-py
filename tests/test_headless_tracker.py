import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modes.headless import run_headless


class HeadlessTrackerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.node = SimpleNamespace(latest_block_hash=None, logger=mock.Mock())
        self.configs = {
            "cli": {
                "on_startup_connect_node": False,
                "on_startup_validate_blockchain": False,
                "on_startup_verify_blockchain": False,
                "latest_block_hash_poll_interval": 10.0,
                "api_port": None,
            },
            "node": {},
        }
        self.mocks = {}
        for name, kwargs in (
            ("start_latest_block_hash_poller", {"return_value": mock.Mock()}),
            ("start_transaction_tracker", {"return_value": (mock.Mock(), mock.Mock())}),
            ("persist_node_latest_block_hash", {}),
            ("load_node_forks", {}),
            ("persist_node_forks", {}),
        ):
            patcher = mock.patch(f"modes.headless.{name}", **kwargs)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def run_headless(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_headless(data_dir=self.data_dir, configs=self.configs, node=self.node)
        return code, out.getvalue()

    def test_headless_starts_and_stops_tracker(self):
        _, stop = self.mocks["start_transaction_tracker"].return_value
        code, _ = self.run_headless()
        self.assertEqual(code, 0)
        self.mocks["start_transaction_tracker"].assert_called_once_with(
            node=self.node, data_dir=self.data_dir, poll_interval=10.0
        )
        stop.assert_called_once_with()

    def test_headless_tracker_start_error_keeps_running(self):
        self.mocks["start_transaction_tracker"].side_effect = OSError("denied")
        code, out = self.run_headless()
        self.assertEqual(code, 0)
        self.assertIn("transaction tracking is off: denied", out)
        self.mocks["start_latest_block_hash_poller"].return_value.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
