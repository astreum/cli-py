import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astreum import format_astre_amount

from modes.tui.pages.menu import MenuPage
from modes.tui.pages.storage import StoragePage, format_bytes
from utils.tx_tracker import ClaimStats


class FakeTracker:
    def __init__(self, stats):
        self.value = stats

    def stats(self):
        return self.value


def provider_node():
    return SimpleNamespace(
        is_storage_provider=True,
        hot_storage_size=1_500,
        cold_storage_size=2_000_000,
        storage_claim_band=3,
        storage_claim_hash_rate=125.5,
        storage_claim_inclusion_delay=2,
        config=SimpleNamespace(
            cold_storage_path="/data/storage",
            hot_storage_limit=64_000_000,
            cold_storage_limit=3_300_000_000,
            storage_claim_fee_window=64,
        ),
    )


def page_text(app):
    page = StoragePage()
    page.load_elements(app=app)
    return page, "\n".join(line for element in page.elements for line in element.render())


class FormatBytesTests(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(999), "999 B")
        self.assertEqual(format_bytes(1_500), "1.5 KB")
        self.assertEqual(format_bytes(2_000_000), "2.0 MB")
        self.assertEqual(format_bytes(3_300_000_000), "3.3 GB")


class StoragePageTests(unittest.TestCase):
    def setUp(self):
        self.stats = ClaimStats(
            sent=10, succeeded=6, failed=1, not_included=2, earned=1000, fees=100
        )
        self.app = SimpleNamespace(node=provider_node(), tx_tracker=FakeTracker(self.stats))

    def row(self, text, label):
        return next(line for line in text.splitlines() if label in line)

    def test_page_shows_node_values(self):
        _, text = page_text(self.app)
        self.assertIn("On", self.row(text, "Long Term Provider"))
        self.assertIn("/data/storage", self.row(text, "Cold Storage Folder"))
        self.assertIn("1.5 KB / 64.0 MB", self.row(text, "Hot Storage"))
        self.assertIn("2.0 MB / 3.3 GB", self.row(text, "Cold Storage  "))
        self.assertIn("3", self.row(text, "Band"))
        self.assertIn("125.5 /s", self.row(text, "Hash Rate"))
        self.assertIn("2 blocks", self.row(text, "Inclusion Delay"))

    def test_page_shows_claim_totals(self):
        _, text = page_text(self.app)
        self.assertTrue(self.row(text, "Sent").rstrip().endswith("10"))
        self.assertTrue(self.row(text, "Succeeded").rstrip().endswith("6"))
        self.assertTrue(self.row(text, "Failed").rstrip().endswith("1"))
        self.assertTrue(self.row(text, "Not Included").rstrip().endswith("2"))
        self.assertTrue(self.row(text, "Waiting for Check").rstrip().endswith("1"))
        self.assertIn(format_astre_amount(1000), self.row(text, "Earned"))
        self.assertIn(format_astre_amount(100), self.row(text, "Fees Paid"))
        self.assertTrue(self.row(text, "Net").rstrip().endswith(format_astre_amount(900)))
        self.assertIn("Checks run 64 blocks after a claim is sent.", text)

    def test_negative_net_has_minus(self):
        self.app.tx_tracker = FakeTracker(ClaimStats(sent=1, failed=1, fees=1500))
        _, text = page_text(self.app)
        self.assertTrue(self.row(text, "Net").rstrip().endswith("-" + format_astre_amount(1500)))

    def test_tracking_off_message(self):
        self.app.tx_tracker = None
        _, text = page_text(self.app)
        self.assertEqual(text.count("Tracking is off."), 2)
        self.assertNotIn("Waiting for Check", text)

    def test_page_draws_with_bare_node(self):
        app = SimpleNamespace(node=SimpleNamespace(config=SimpleNamespace()), tx_tracker=None)
        page, text = page_text(app)
        self.assertIn("Off", self.row(text, "Long Term Provider"))
        self.assertIn("Disabled", self.row(text, "Cold Storage Folder"))
        self.assertIn("Not measured", self.row(text, "Hash Rate"))
        page.render()

    def test_values_update_on_next_load(self):
        page, _ = page_text(self.app)
        self.app.tx_tracker.value = ClaimStats(sent=42)
        page.load_elements(app=self.app)
        text = "\n".join(line for element in page.elements for line in element.render())
        self.assertTrue(self.row(text, "Sent").rstrip().endswith("42"))

    def test_page_has_no_selectable_element(self):
        page, _ = page_text(self.app)
        self.assertFalse(page.has_selectable())
        self.assertEqual(page.title, "Storage")


class StoragePageIndexTests(unittest.TestCase):
    def setUp(self):
        node = provider_node()
        node.latest_block = SimpleNamespace(height=12157)
        node.peers = {"a": 1, "b": 2}
        node.storage_index = {bytes(32): (0,), bytes([1]) * 32: (0, 1), bytes([2]) * 32: (1,)}
        node.storage_providers = [b"p0", b"p1"]
        node.index_requested = True
        node.startup_announce = "done"
        node.new_record_ids = [bytes(32)]
        self.app = SimpleNamespace(node=node, tx_tracker=None)

    def row(self, text, label):
        return next(line for line in text.splitlines() if line.strip().startswith(label))

    def test_index_section_shows_node_values(self):
        _, text = page_text(self.app)
        self.assertIn("INDEX", text)
        self.assertTrue(self.row(text, "Latest Block").rstrip().endswith("#12157"))
        self.assertTrue(self.row(text, "Peers").rstrip().endswith("2"))
        self.assertTrue(self.row(text, "Index Entries").rstrip().endswith("3"))
        self.assertTrue(self.row(text, "Known Providers").rstrip().endswith("2"))
        self.assertTrue(self.row(text, "Index Requested").rstrip().endswith("Yes"))
        self.assertTrue(self.row(text, "Startup Announce").rstrip().endswith("Done"))
        self.assertTrue(self.row(text, "New Records Queued").rstrip().endswith("1"))

    def test_index_section_comes_after_claim_worker(self):
        page, _ = page_text(self.app)
        headers = [element.label for element in page.elements if element.header]
        self.assertEqual(headers.index("INDEX"), headers.index("CLAIM WORKER") + 1)

    def test_startup_announce_states(self):
        node = self.app.node
        node.startup_announce = None
        _, text = page_text(self.app)
        self.assertTrue(self.row(text, "Startup Announce").rstrip().endswith("Waiting"))
        node.startup_announce = iter(())
        _, text = page_text(self.app)
        self.assertTrue(self.row(text, "Startup Announce").rstrip().endswith("Running"))

    def test_index_section_with_bare_node(self):
        app = SimpleNamespace(node=SimpleNamespace(config=SimpleNamespace()), tx_tracker=None)
        _, text = page_text(app)
        self.assertTrue(self.row(text, "Latest Block").rstrip().endswith("Not loaded"))
        self.assertTrue(self.row(text, "Peers").rstrip().endswith("0"))
        self.assertTrue(self.row(text, "Index Entries").rstrip().endswith("0"))
        self.assertTrue(self.row(text, "Known Providers").rstrip().endswith("0"))
        self.assertTrue(self.row(text, "Index Requested").rstrip().endswith("No"))
        self.assertTrue(self.row(text, "Startup Announce").rstrip().endswith("Off"))
        self.assertTrue(self.row(text, "New Records Queued").rstrip().endswith("Off"))


class MenuTests(unittest.TestCase):
    def test_menu_has_storage_before_settings(self):
        page = MenuPage()
        page.load_elements()
        labels = [element.label for element in page.elements]
        self.assertEqual(labels.index("Storage") + 1, labels.index("Settings"))
        storage = page.elements[labels.index("Storage")]
        self.assertEqual(storage.next, "storage")


if __name__ == "__main__":
    unittest.main()
