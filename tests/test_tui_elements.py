import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modes.tui.element import PageElement


class ElementTests(unittest.TestCase):
    def test_header_is_not_selectable(self):
        element = PageElement(label="STORAGE", header=True)
        self.assertFalse(element.selectable)
        first = element.render(focus=True)[0]
        self.assertIn("STORAGE", first)
        self.assertNotIn(">", first)

    def test_plain_element_is_selectable(self):
        self.assertTrue(PageElement(label="x").selectable)

    def test_enabled_callable_is_read_each_time(self):
        flag = [False]
        element = PageElement(label="x", enabled=lambda: flag[0])
        self.assertFalse(element.selectable)
        flag[0] = True
        self.assertTrue(element.selectable)

    def test_disabled_element_has_no_focus_prefix(self):
        element = PageElement(label="x", enabled=False)
        self.assertFalse(element.render(focus=True)[0].startswith(">"))

    def test_option_renders_all_choices(self):
        element = PageElement(label="Long Term Provider", options=["Off", "On"])
        self.assertEqual(
            element.render(focus=True),
            ["> Long Term Provider", "  [x] Off  [ ] On"],
        )
        element = PageElement(
            label="Long Term Provider", options=["Off", "On"], selected=1
        )
        self.assertEqual(
            element.render(focus=False),
            ["  Long Term Provider", "  [ ] Off  [x] On"],
        )

    def test_cycle_option_wraps(self):
        element = PageElement(label="x", options=["Off", "On"])
        self.assertEqual(element.selected_option, "Off")
        element.cycle_option()
        self.assertEqual(element.selected_option, "On")
        element.cycle_option()
        self.assertEqual(element.selected_option, "Off")

    def test_selected_option_is_none_without_options(self):
        self.assertIsNone(PageElement(label="x").selected_option)


if __name__ == "__main__":
    unittest.main()
