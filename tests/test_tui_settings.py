import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modes.tui.pages.settings import SettingsPage

SAVED_MESSAGE = "Storage settings saved. Restart the CLI to apply."


class SettingsStorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        self.settings_path = self.data_dir / "settings.json"

    def make(self, node_config=None):
        app = SimpleNamespace(
            data_dir=self.data_dir,
            configs={"cli": {}, "node": dict(node_config or {})},
            flash_message=None,
        )
        page = SettingsPage()
        page.load_elements(app=app)
        return app, page

    def test_layout(self):
        _, page = self.make()
        self.assertEqual(
            [e.label for e in page.elements],
            [
                "VALIDATION",
                "Account Name",
                "Save Validation Key",
                "Delete Validation Key",
                "STORAGE",
                "Long Term Provider",
                "Save Storage Settings",
            ],
        )
        self.assertTrue(page.elements[0].header)
        self.assertTrue(page.elements[4].header)

    def test_option_starts_from_config(self):
        _, page = self.make({"is_storage_provider": True})
        self.assertEqual(page.elements[5].selected_option, "On")
        _, page = self.make()
        self.assertEqual(page.elements[5].selected_option, "Off")

    def test_save_button_disabled_until_changed(self):
        _, page = self.make()
        self.assertFalse(page.elements[6].selectable)
        page.index = 5
        page.navigate(forward=True)
        self.assertEqual(page.index, 1)
        page.elements[5].cycle_option()
        self.assertTrue(page.elements[6].selectable)
        page.index = 5
        page.navigate(forward=True)
        self.assertEqual(page.index, 6)

    def test_toggle_back_disables_save(self):
        _, page = self.make()
        page.elements[5].cycle_option()
        page.elements[5].cycle_option()
        self.assertFalse(page.elements[6].selectable)

    def test_save_writes_only_the_key(self):
        self.settings_path.write_text(
            json.dumps({"cli": {"api_port": 1}, "node": {"x": 2}}), encoding="utf-8"
        )
        app, page = self.make()
        page.elements[5].cycle_option()
        page._handle_storage_save(app)
        self.assertEqual(
            json.loads(self.settings_path.read_text(encoding="utf-8")),
            {"cli": {"api_port": 1}, "node": {"x": 2, "is_storage_provider": True}},
        )
        self.assertIs(app.configs["node"]["is_storage_provider"], True)
        self.assertEqual(app.flash_message, SAVED_MESSAGE)

    def test_save_creates_missing_file(self):
        app, page = self.make()
        page.elements[5].cycle_option()
        page._handle_storage_save(app)
        self.assertEqual(
            json.loads(self.settings_path.read_text(encoding="utf-8")),
            {"node": {"is_storage_provider": True}},
        )

    def test_save_with_invalid_json_flashes_and_keeps_file(self):
        self.settings_path.write_text("{not json", encoding="utf-8")
        app, page = self.make()
        page.elements[5].cycle_option()
        page._handle_storage_save(app)
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), "{not json")
        self.assertIsNotNone(app.flash_message)
        self.assertNotEqual(app.flash_message, SAVED_MESSAGE)
        self.assertNotIn("is_storage_provider", app.configs["node"])

    def test_focus_lands_on_option_after_save(self):
        app, page = self.make()
        page.elements[5].cycle_option()
        page.index = 6
        page._handle_storage_save(app)
        page.load_elements(app=app)
        page.ensure_focus()
        self.assertEqual(page.index, 5)
        self.assertEqual(page.elements[5].selected_option, "On")


if __name__ == "__main__":
    unittest.main()
