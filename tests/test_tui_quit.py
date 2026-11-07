import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modes.tui.model import App, run_tui, shutdown_node

CLAIM_VALUES = {
    "storage_claim_band": 3,
    "storage_claim_hash_rate": 125.5,
    "storage_claim_inclusion_delay": None,
}
INTERRUPT_LINE = "Node stop interrupted. The claim values are not saved."
RESTORE = "\x1b[?1049l"


class ShutdownNodeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.settings_path = self.data_dir / "settings.json"
        self.app = SimpleNamespace(
            data_dir=self.data_dir,
            configs={"cli": {}, "node": {}},
            node=SimpleNamespace(is_connected=True, is_storage_provider=True),
            flash_now=mock.Mock(),
        )
        patcher = mock.patch("modes.tui.model.disconnect_node", return_value=dict(CLAIM_VALUES))
        self.disconnect = patcher.start()
        self.addCleanup(patcher.stop)

    def read_json(self):
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    def test_not_connected_skips_stop(self):
        self.app.node.is_connected = False
        self.assertEqual(shutdown_node(self.app), [])
        self.disconnect.assert_not_called()
        self.app.flash_now.assert_not_called()

    def test_not_provider_stops_without_save(self):
        self.app.configs["node"]["is_storage_provider"] = True
        self.app.node.is_storage_provider = False
        self.assertEqual(shutdown_node(self.app), [])
        self.disconnect.assert_called_once_with(self.app.node)
        self.assertFalse(self.settings_path.exists())

    def test_provider_saves_values_that_are_set(self):
        self.settings_path.write_text(
            json.dumps({"cli": {"api_port": 1}, "node": {"is_storage_provider": True}}),
            encoding="utf-8",
        )
        self.assertEqual(shutdown_node(self.app), [])
        self.app.flash_now.assert_called_once_with("Stopping node")
        self.assertEqual(
            self.read_json(),
            {
                "cli": {"api_port": 1},
                "node": {
                    "is_storage_provider": True,
                    "storage_claim_band": 3,
                    "storage_claim_hash_rate": 125.5,
                },
            },
        )

    def test_provider_with_no_values_writes_nothing(self):
        self.disconnect.return_value = dict.fromkeys(CLAIM_VALUES)
        self.assertEqual(shutdown_node(self.app), [])
        self.assertFalse(self.settings_path.exists())

    def test_stop_error_returns_one_line(self):
        self.disconnect.side_effect = RuntimeError("boom")
        self.assertEqual(shutdown_node(self.app), ["Failed to stop the node: boom"])
        self.assertFalse(self.settings_path.exists())

    def test_save_error_returns_one_line(self):
        self.settings_path.write_text("{not json", encoding="utf-8")
        errors = shutdown_node(self.app)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("Failed to save the claim values: "))
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), "{not json")

    def test_flash_error_still_stops(self):
        self.app.flash_now.side_effect = RuntimeError("draw failed")
        self.assertEqual(shutdown_node(self.app), [])
        self.disconnect.assert_called_once_with(self.app.node)
        self.assertEqual(self.read_json()["node"]["storage_claim_band"], 3)


class RunTuiQuitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.app = SimpleNamespace(
            should_exit=True,
            data_dir=Path(self._tmp.name),
            node=SimpleNamespace(latest_block_hash=b"\x01" * 32, logger=mock.Mock()),
        )
        self.mocks = {}
        for name, kwargs in (
            ("App", {"return_value": self.app}),
            ("KeyboardInput", {}),
            ("render_app", {}),
            ("persist_node_latest_block_hash", {}),
            ("shutdown_node", {"return_value": []}),
        ):
            patcher = mock.patch(f"modes.tui.model.{name}", **kwargs)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def run_tui(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = run_tui(data_dir=self.app.data_dir, configs={}, node=None)
        return code, out.getvalue()

    def test_errors_print_after_terminal_restore(self):
        self.mocks["shutdown_node"].return_value = ["Failed to stop the node: boom"]
        code, out = self.run_tui()
        self.assertEqual(code, 0)
        self.assertLess(out.index(RESTORE), out.index("Failed to stop the node: boom"))

    def test_stop_comes_before_hash_save(self):
        parent = mock.Mock()
        parent.attach_mock(self.mocks["shutdown_node"], "shutdown_node")
        parent.attach_mock(self.mocks["persist_node_latest_block_hash"], "persist")
        self.run_tui()
        self.assertEqual([c[0] for c in parent.mock_calls], ["shutdown_node", "persist"])

    def test_interrupt_during_stop_still_restores_and_saves_hash(self):
        self.mocks["shutdown_node"].side_effect = KeyboardInterrupt
        code, out = self.run_tui()
        self.assertEqual(code, 0)
        self.assertLess(out.index(RESTORE), out.index(INTERRUPT_LINE))
        self.mocks["persist_node_latest_block_hash"].assert_called_once()

    def test_interrupt_during_poller_stop_still_restores_and_saves_hash(self):
        self.app.stop_latest_block_poller = mock.Mock(side_effect=KeyboardInterrupt)
        code, out = self.run_tui()
        self.assertEqual(code, 0)
        self.assertLess(out.index(RESTORE), out.index(INTERRUPT_LINE))
        self.mocks["persist_node_latest_block_hash"].assert_called_once()

    def test_tracker_stops_before_node_stop(self):
        self.app.stop_tx_tracker = mock.Mock()
        parent = mock.Mock()
        parent.attach_mock(self.app.stop_tx_tracker, "stop_tx_tracker")
        parent.attach_mock(self.mocks["shutdown_node"], "shutdown_node")
        parent.attach_mock(self.mocks["persist_node_latest_block_hash"], "persist")
        self.run_tui()
        self.assertEqual(
            [c[0] for c in parent.mock_calls], ["stop_tx_tracker", "shutdown_node", "persist"]
        )

    def test_interrupt_during_tracker_stop_still_restores(self):
        self.app.stop_tx_tracker = mock.Mock(side_effect=KeyboardInterrupt)
        code, out = self.run_tui()
        self.assertEqual(code, 0)
        self.assertLess(out.index(RESTORE), out.index(INTERRUPT_LINE))
        self.mocks["persist_node_latest_block_hash"].assert_called_once()


class AppTrackerStartTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.node = SimpleNamespace(logger=mock.Mock())
        for target, kwargs in (
            ("modes.tui.model.start_latest_block_hash_poller", {"return_value": mock.Mock()}),
            ("modes.tui.model.App._run_cli_startup_actions", {}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch("modes.tui.model.start_transaction_tracker")
        self.start_tracker = patcher.start()
        self.addCleanup(patcher.stop)

    def make_app(self):
        configs = {"cli": {"latest_block_hash_poll_interval": 10.0}, "node": {}}
        return App(data_dir=self.data_dir, configs=configs, node=self.node)

    def test_app_starts_tracker(self):
        tracker, stop = mock.Mock(), mock.Mock()
        self.start_tracker.return_value = (tracker, stop)
        app = self.make_app()
        self.start_tracker.assert_called_once_with(
            node=self.node, data_dir=self.data_dir, poll_interval=10.0
        )
        self.assertIs(app.tx_tracker, tracker)
        app.stop_tx_tracker()
        stop.assert_called_once_with()

    def test_app_tracker_start_error_turns_tracking_off(self):
        self.start_tracker.side_effect = OSError("denied")
        app = self.make_app()
        self.assertIsNone(app.tx_tracker)
        self.assertIsNone(app.stop_tx_tracker())
        self.node.logger.warning.assert_called()


if __name__ == "__main__":
    unittest.main()
