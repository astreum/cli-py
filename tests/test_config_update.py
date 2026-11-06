import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import update_node_settings


class UpdateNodeSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.path = self.data_dir / "settings.json"
        self.tmp_path = self.data_dir / "settings.json.tmp"

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def read_json(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_missing_file_is_created(self):
        update_node_settings(self.data_dir, {"storage_claim_band": 3})
        self.assertEqual(self.read_json(), {"node": {"storage_claim_band": 3}})

    def test_other_keys_stay(self):
        self.write(json.dumps({"cli": {"api_port": 1}, "node": {"x": 2, "storage_claim_band": 1}}))
        update_node_settings(
            self.data_dir, {"storage_claim_band": 4, "storage_claim_hash_rate": 125.5}
        )
        self.assertEqual(
            self.read_json(),
            {
                "cli": {"api_port": 1},
                "node": {"x": 2, "storage_claim_band": 4, "storage_claim_hash_rate": 125.5},
            },
        )

    def test_format_matches_save_config(self):
        self.write(json.dumps({"node": {"b": 1}, "cli": {}}))
        update_node_settings(self.data_dir, {"a": True})
        expected = {"cli": {}, "node": {"a": True, "b": 1}}
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            json.dumps(expected, indent=2, sort_keys=True),
        )

    def test_invalid_json_raises_and_keeps_file(self):
        self.write("{not json")
        with self.assertRaises(ValueError):
            update_node_settings(self.data_dir, {"a": 1})
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not json")

    def test_list_root_raises(self):
        self.write("[]")
        with self.assertRaisesRegex(ValueError, "^settings.json must hold a JSON object$"):
            update_node_settings(self.data_dir, {"a": 1})
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[]")

    def test_null_node_raises(self):
        self.write('{"node": null}')
        with self.assertRaisesRegex(
            ValueError, '^settings.json "node" must be a JSON object$'
        ):
            update_node_settings(self.data_dir, {"a": 1})
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"node": null}')

    def test_no_tmp_left_after_save(self):
        update_node_settings(self.data_dir, {"a": 1})
        self.assertFalse(self.tmp_path.exists())

    def test_replace_failure_keeps_file_and_removes_tmp(self):
        self.write('{"node": {"x": 1}}')
        with mock.patch("utils.config.os.replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                update_node_settings(self.data_dir, {"a": 1})
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"node": {"x": 1}}')
        self.assertFalse(self.tmp_path.exists())


if __name__ == "__main__":
    unittest.main()
