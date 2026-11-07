from __future__ import annotations

from typing import Any, List, Optional, Tuple

from astreum import format_astre_amount

from ..base import BasePage
from ..element import PageElement

LABEL_WIDTH = 21
TRACKING_OFF = "Tracking is off."


def format_bytes(n: int) -> str:
    """Return a byte count in B, KB, MB or GB (base 1000, one decimal place)."""
    if n < 1000:
        return f"{n} B"
    for unit, size in (("GB", 10**9), ("MB", 10**6), ("KB", 10**3)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} B"


def _rows(rows: List[Tuple[str, Any]]) -> str:
    return "\n".join(f"{label:<{LABEL_WIDTH}}{value}" for label, value in rows)


def _signed_amount(amount: int) -> str:
    if amount < 0:
        return "-" + format_astre_amount(-amount)
    return format_astre_amount(amount)


class _TextElement(PageElement):
    """A disabled element that draws only its body, with no label line."""

    def __init__(self, text: str) -> None:
        super().__init__(label="", body=text, enabled=False)

    def render(self, focus: bool = False) -> List[str]:
        return [f"  {line}" for line in self.body.split("\n")]


class StoragePage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Storage", elements=[])

    def load_elements(self, app: "App", *args, **kwargs):
        node = app.node
        config = getattr(node, "config", None)
        tracker = getattr(app, "tx_tracker", None)
        stats = tracker.stats() if tracker is not None else None
        self.elements = [
            *self._section("ROLE", self._role(node, config)),
            *self._section("SPACE", self._space(node, config)),
            *self._section("CLAIM WORKER", self._worker(node)),
            *self._section("CLAIMS", self._claims(stats)),
            *self._section("EARNINGS", self._earnings(stats, config)),
        ]

    @staticmethod
    def _section(title: str, body: str) -> List[PageElement]:
        return [
            PageElement(label=title, header=True),
            _TextElement(body),
        ]

    @staticmethod
    def _role(node, config) -> str:
        provider = getattr(node, "is_storage_provider", False)
        folder = getattr(config, "cold_storage_path", None)
        return _rows(
            [
                ("Long Term Provider", "On" if provider else "Off"),
                ("Cold Storage Folder", folder or "Disabled"),
            ]
        )

    @staticmethod
    def _space(node, config) -> str:
        def usage(size_name: str, limit_name: str) -> str:
            used = getattr(node, size_name, None) or 0
            limit = getattr(config, limit_name, None)
            limit_text = format_bytes(limit) if limit is not None else "Not set"
            return f"{format_bytes(used)} / {limit_text}"

        return _rows(
            [
                ("Hot Storage", usage("hot_storage_size", "hot_storage_limit")),
                ("Cold Storage", usage("cold_storage_size", "cold_storage_limit")),
            ]
        )

    @staticmethod
    def _worker(node) -> str:
        band = getattr(node, "storage_claim_band", None)
        rate = getattr(node, "storage_claim_hash_rate", None)
        delay = getattr(node, "storage_claim_inclusion_delay", None)
        return _rows(
            [
                ("Band", band if band is not None else "Not set"),
                ("Hash Rate", f"{rate:.1f} /s" if rate else "Not measured"),
                ("Inclusion Delay", f"{delay} blocks" if delay is not None else "Not measured"),
            ]
        )

    @staticmethod
    def _claims(stats) -> str:
        if stats is None:
            return TRACKING_OFF
        return _rows(
            [
                ("Sent", stats.sent),
                ("Succeeded", stats.succeeded),
                ("Failed", stats.failed),
                ("Not Included", stats.not_included),
                ("Waiting for Check", stats.waiting),
            ]
        )

    @staticmethod
    def _earnings(stats, config) -> str:
        if stats is None:
            return TRACKING_OFF
        text = _rows(
            [
                ("Earned", format_astre_amount(stats.earned)),
                ("Fees Paid", format_astre_amount(stats.fees)),
                ("Net", _signed_amount(stats.net)),
            ]
        )
        window: Optional[int] = getattr(config, "storage_claim_fee_window", None)
        if window is not None:
            text += f"\nChecks run {window} blocks after a claim is sent."
        return text
