import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import build_node_config


class BuildNodeConfigSentLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        patcher = mock.patch("utils.config.load_or_create_storage_key", return_value="0x00")
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, node):
        configs = {"cli": {}, "node": node}
        return configs, build_node_config(configs, self.data_dir)

    def test_sets_sent_log_path_in_data_dir(self):
        _, node_config = self.build({})
        self.assertEqual(
            node_config["sent_transactions_path"],
            str(self.data_dir / "sent_transactions.csv"),
        )

    def test_keeps_explicit_path(self):
        _, node_config = self.build({"sent_transactions_path": "/x.csv"})
        self.assertEqual(node_config["sent_transactions_path"], "/x.csv")

    def test_explicit_null_keeps_log_off(self):
        _, node_config = self.build({"sent_transactions_path": None})
        self.assertIsNone(node_config["sent_transactions_path"])

    def test_does_not_change_configs(self):
        configs, _ = self.build({})
        self.assertNotIn("sent_transactions_path", configs["node"])


if __name__ == "__main__":
    unittest.main()
