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

from modes.tui.base import BasePage
from modes.tui.element import PageElement
from modes.tui.model import App
from modes.tui.pages.accounts.create import AccountCreatePage
from modes.tui.render import build_flash_line, render_app


def make_page(elements, title="t"):
    page = BasePage(title=title)
    page.elements = elements
    return page


def make_app(pages=None, active_view="menu"):
    app = App.__new__(App)
    app.pages = pages or {"menu": make_page([PageElement("A")])}
    app.active_view = active_view
    app.previous_view = None
    app.input_focus = False
    app.flash_message = None
    app.flash_level = "info"
    app.header_block = []
    app.node = SimpleNamespace(
        latest_block_hash=None,
        is_connected=False,
        peers={},
        config=SimpleNamespace(chain="test"),
    )
    app.lines = []
    app.line_offset = 0
    app.body_lines = None
    app.cursor_position = None
    return app


def render(app):
    with contextlib.redirect_stdout(io.StringIO()):
        render_app(app)


class FlashLineTests(unittest.TestCase):
    def test_no_text_is_empty(self):
        self.assertEqual(build_flash_line(None, "info", 80), "")
        self.assertEqual(build_flash_line("", "error", 80), "")

    def test_levels(self):
        self.assertEqual(build_flash_line("hi", "info", 80), "hi")
        self.assertEqual(build_flash_line("ok", "success", 80), "\x1b[32mok\x1b[0m")
        self.assertEqual(build_flash_line("bad", "error", 80), "\x1b[31mbad\x1b[0m")
        self.assertEqual(
            build_flash_line("Stopping node", "busy", 80),
            "\x1b[33mStopping node\u2026\x1b[0m",
        )

    def test_cut_busy_text_keeps_ellipsis(self):
        self.assertEqual(
            build_flash_line("Stopping node", "busy", 15),
            "\x1b[33mStopp\u2026\x1b[0m",
        )

    def test_newline_becomes_space(self):
        self.assertEqual(build_flash_line("a\nb", "info", 80), "a b")

    def test_long_text_fits_width_and_ends_with_reset(self):
        line = build_flash_line("x" * 100, "error", 20)
        self.assertLessEqual(len(line), 20)
        self.assertTrue(line.startswith("\x1b[31mx"))
        self.assertTrue(line.endswith("\x1b[0m"))

    def test_tiny_width_returns_plain_text(self):
        self.assertEqual(build_flash_line("bad", "error", 5), "bad")
        self.assertEqual(build_flash_line("toolong", "error", 5), "toolo")


class FlashApiTests(unittest.TestCase):
    def test_flash_sets_text_and_level(self):
        app = make_app()
        app.flash("x", "error")
        self.assertEqual((app.flash_message, app.flash_level), ("x", "error"))

    def test_flash_default_level_is_info(self):
        app = make_app()
        app.flash("x")
        self.assertEqual(app.flash_level, "info")

    def test_unknown_level_raises(self):
        app = make_app()
        with self.assertRaises(ValueError):
            app.flash("x", "warn")

    def test_clear_flash(self):
        app = make_app()
        app.flash("x", "error")
        app.clear_flash()
        self.assertEqual((app.flash_message, app.flash_level), (None, "info"))

    def test_flash_now_draws_once(self):
        app = make_app()
        with mock.patch("modes.tui.model.render_app") as draw_frame:
            app.flash_now("Stopping node")
        draw_frame.assert_called_once_with(app)
        self.assertEqual((app.flash_message, app.flash_level), ("Stopping node", "busy"))


class FlashSlotTests(unittest.TestCase):
    def test_slot_keeps_body_in_place(self):
        app = make_app()
        render(app)
        start = app.body_lines[0]
        self.assertEqual(app.lines[start - 2], "")

        app.flash_message = "hello"
        app.flash_level = "error"
        render(app)
        self.assertEqual(app.body_lines[0], start)
        self.assertIn("hello", app.lines[start - 2])


class PageChangeTests(unittest.TestCase):
    def make(self, elements=None):
        page = make_page(elements or [PageElement("A")])
        pages = {"p": page, "q": make_page([PageElement("B")]), "menu": make_page([PageElement("M")])}
        return make_app(pages=pages, active_view="p")

    def test_go_to_clears_flash(self):
        app = self.make()
        app.flash("x", "error")
        app.go_to("q", previous="p")
        self.assertEqual(
            (app.active_view, app.previous_view, app.flash_message), ("q", "p", None)
        )

    def test_flash_after_go_to_stays(self):
        app = self.make()
        app.go_to("q")
        app.flash("done", "success")
        self.assertEqual(app.flash_message, "done")

    def test_enter_on_link_changes_page_and_clears_flash(self):
        app = self.make([PageElement("Go", next="q")])
        app.flash("x")
        app.handle_enter()
        self.assertEqual(
            (app.active_view, app.previous_view, app.flash_message), ("q", "p", None)
        )

    def test_esc_goes_back_at_first_press(self):
        app = self.make()
        app.previous_view = "q"
        app.flash("x", "error")
        app.handle_return()
        self.assertEqual(
            (app.active_view, app.previous_view, app.flash_message), ("q", None, None)
        )

    def test_esc_without_previous_goes_to_menu(self):
        app = self.make()
        app.handle_return()
        self.assertEqual(app.active_view, "menu")

    def test_esc_with_input_focus_keeps_flash(self):
        app = self.make()
        app.input_focus = True
        app.flash("Invalid hex in Address.", "error")
        app.handle_return()
        self.assertEqual(
            (app.input_focus, app.active_view, app.flash_message),
            (False, "p", "Invalid hex in Address."),
        )


class AccountCreateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name)
        (self.data_dir / "accounts").mkdir()
        self.page = AccountCreatePage()
        self.page.load_elements()
        self.page.elements[0].input = ["alice"]
        self.app = make_app(
            pages={"account_create": self.page, "account_list": make_page([])},
            active_view="account_create",
        )
        self.app.data_dir = self.data_dir

    def test_create_write_failure_stays_on_page_with_error(self):
        with mock.patch.object(Path, "write_text", side_effect=OSError("disk full")):
            self.page.handle_submit(self.app)
        self.assertEqual(self.app.active_view, "account_create")
        self.assertIn("disk full", self.app.flash_message)

    def test_create_success_goes_to_list(self):
        self.page.handle_submit(self.app)
        self.assertEqual(
            (self.app.active_view, self.app.previous_view),
            ("account_list", "account_create"),
        )
        self.assertTrue((self.data_dir / "accounts" / "alice.txt").exists())


if __name__ == "__main__":
    unittest.main()
