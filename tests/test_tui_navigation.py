import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modes.tui.base import BasePage
from modes.tui.element import PageElement
from modes.tui.model import App
from modes.tui.render import scroll_to_span


def make_page(elements, index=0):
    page = BasePage(title="t")
    page.elements = elements
    page.index = index
    return page


class NavigationTests(unittest.TestCase):
    def test_navigate_skips_header(self):
        page = make_page([PageElement("H", header=True), PageElement("A"), PageElement("B")])
        page.ensure_focus()
        self.assertEqual(page.index, 1)
        page.navigate(forward=True)
        self.assertEqual(page.index, 2)
        page.navigate(forward=True)
        self.assertEqual(page.index, 1)

    def test_navigate_skips_disabled_button(self):
        page = make_page(
            [PageElement("A"), PageElement("B", enabled=False), PageElement("C")]
        )
        page.navigate(forward=True)
        self.assertEqual(page.index, 2)
        page.navigate(forward=False)
        self.assertEqual(page.index, 0)

    def test_navigate_backward_wraps_past_header(self):
        page = make_page(
            [PageElement("H", header=True), PageElement("A"), PageElement("B")], index=1
        )
        page.navigate(forward=False)
        self.assertEqual(page.index, 2)

    def test_navigate_with_nothing_selectable_does_nothing(self):
        page = make_page([PageElement("H", header=True), PageElement("B", enabled=False)])
        page.navigate(forward=True)
        self.assertEqual(page.index, 0)
        page.navigate(forward=False)
        self.assertEqual(page.index, 0)

    def test_ensure_focus_moves_off_disabled(self):
        page = make_page([PageElement("A", enabled=False), PageElement("B")])
        page.ensure_focus()
        self.assertEqual(page.index, 1)

    def test_ensure_focus_clamps_index_after_shrink(self):
        page = make_page([PageElement("A"), PageElement("B"), PageElement("C")], index=2)
        page.elements = [PageElement("A")]
        page.ensure_focus()
        self.assertEqual(page.index, 0)

    def test_element_spans_cover_each_element(self):
        page = make_page([PageElement("A"), PageElement("B", input=[""])])
        page.render_with_cursor()
        self.assertEqual(page.element_spans, [(2, 2), (4, 5)])


class ScrollTests(unittest.TestCase):
    def test_scroll_to_span_no_change_when_visible(self):
        self.assertEqual(scroll_to_span(5, 10, 6, 8), 5)

    def test_scroll_to_span_scrolls_up(self):
        self.assertEqual(scroll_to_span(5, 10, 2, 3), 2)

    def test_scroll_to_span_scrolls_down(self):
        self.assertEqual(scroll_to_span(0, 10, 12, 13), 4)

    def test_scroll_to_span_taller_than_window_shows_start(self):
        self.assertEqual(scroll_to_span(0, 3, 10, 20), 10)

    def test_scroll_to_span_taller_than_window_keeps_offset_inside_span(self):
        self.assertEqual(scroll_to_span(12, 3, 10, 20), 12)

    def test_scroll_to_span_taller_than_window_clamps_past_the_end(self):
        self.assertEqual(scroll_to_span(30, 3, 10, 20), 18)


def make_app(page):
    app = App.__new__(App)
    app.pages = {"p": page}
    app.active_view = "p"
    app.input_focus = False
    app.previous_view = None
    app.flash_message = None
    app.lines = ["x"] * 50
    app.window_rows = 10
    app.line_offset = 5
    app.body_lines = None
    return app


class AppKeyTests(unittest.TestCase):
    def test_enter_cycles_option(self):
        element = PageElement("Opt", options=["Off", "On"])
        app = make_app(make_page([element]))
        app.handle_enter()
        self.assertEqual(element.selected_option, "On")

    def test_enter_on_disabled_element_does_nothing(self):
        calls = []
        element = PageElement("Btn", action=lambda app: calls.append(app), enabled=False)
        app = make_app(make_page([element]))
        app.handle_enter()
        self.assertEqual(calls, [])

    def test_arrow_on_page_with_selectable_elements_keeps_line_offset(self):
        page = make_page([PageElement("A"), PageElement("B")])
        app = make_app(page)
        app.handle_special_key("B")
        self.assertEqual(page.index, 1)
        self.assertEqual(app.line_offset, 5)

    def test_arrow_on_page_without_selectable_elements_scrolls_lines(self):
        page = make_page([PageElement("H", header=True)])
        app = make_app(page)
        app.handle_special_key("B")
        self.assertEqual(app.line_offset, 6)
        app.handle_special_key("A")
        self.assertEqual(app.line_offset, 5)

    def make_tall_app(self, offset):
        page = make_page(
            [PageElement("Tall", body="\n".join(["l"] * 20)), PageElement("B")]
        )
        page.render_with_cursor()
        self.assertEqual(page.element_spans[0], (2, 22))
        app = make_app(page)
        app.body_lines = (0, 40)
        app.line_offset = offset
        return app, page

    def test_down_scrolls_inside_a_tall_focused_element(self):
        app, page = self.make_tall_app(offset=2)
        for _ in range(11):
            app.handle_special_key("B")
        self.assertEqual((app.line_offset, page.index), (13, 0))
        app.handle_special_key("B")
        self.assertEqual(page.index, 1)

    def test_up_scrolls_inside_a_tall_focused_element(self):
        app, page = self.make_tall_app(offset=4)
        app.handle_special_key("A")
        app.handle_special_key("A")
        self.assertEqual((app.line_offset, page.index), (2, 0))
        app.handle_special_key("A")
        self.assertEqual(page.index, 1)


if __name__ == "__main__":
    unittest.main()
