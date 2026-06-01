from __future__ import annotations

import hashlib

from ..base import BasePage
from ..element import PageElement

from astreum.crypto.bloom_search import bloom_search_tx


class SearchTransactionPage(BasePage):
    def __init__(self):
        super().__init__(title="Search Transaction")
        self.flag_hash = False
        self.flag_data = False
        self._results_body = "Search for results!"
        self._saved_inputs: dict[str, str] = {}

    def load_elements(self, *args, **kwargs):
        # Save current input values before any rebuild
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        if self.elements == []:
            self._rebuild()

    def _input(self, label: str) -> str:
        return self._saved_inputs.get(label, "")

    def _rebuild(self):
        id_val = self._input("ID")
        sender_val = self._input("Sender")
        recipient_val = self._input("Recipient")

        flag_hash_label = "  flag_hash" + ("  [ON]" if self.flag_hash else "  [OFF]")
        flag_data_label = "  flag_data" + ("  [ON]" if self.flag_data else "  [OFF]")

        self.elements = [
            PageElement(label="  Filter"),
            PageElement(label="  ID", input=[id_val]),
            PageElement(label="  Sender", input=[sender_val]),
            PageElement(label="  Recipient", input=[recipient_val]),
            PageElement(label=flag_hash_label, action=self._toggle_flag_hash),
            PageElement(label=flag_data_label, action=self._toggle_flag_data),
            PageElement(label="[Search]", action=self._do_search),
            PageElement(label="  Results"),
            PageElement(label="", body=self._results_body),
        ]

    def _toggle_flag_hash(self, app):
        self.flag_hash = not self.flag_hash
        if self.flag_hash:
            self.flag_data = False
        self.elements = []

    def _toggle_flag_data(self, app):
        self.flag_data = not self.flag_data
        if self.flag_data:
            self.flag_hash = False
        self.elements = []

    @staticmethod
    def _hex_or_hash(value: str, do_hash: bool) -> bytes:
        """Convert user input to bytes.
        If do_hash is True, hash the input string.
        Otherwise treat the input as a hex-encoded byte string.
        """
        if do_hash:
            return hashlib.sha256(value.encode("utf-8")).digest()
        return bytes.fromhex(value)

    def _do_search(self, app):
        # Save inputs
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        id_val = self._input("ID")
        sender_val = self._input("Sender")
        recipient_val = self._input("Recipient")

        # Validate: at least one field must be non-empty
        if not any([id_val, sender_val, recipient_val]):
            app.flash_message = "Provide at least one of: ID, Sender, Recipient"
            return

        # Convert fields to bytes
        do_hash = self.flag_data  # flag_data means hash, flag_hash means raw hex
        try:
            tx_hash_bytes = self._hex_or_hash(id_val, do_hash) if id_val else b""
            sender_bytes = self._hex_or_hash(sender_val, do_hash) if sender_val else b""
            recipient_bytes = self._hex_or_hash(recipient_val, do_hash) if recipient_val else b""
        except ValueError:
            app.flash_message = "Invalid hex in input (try toggling flag_data to hash)"
            return

        # Search from latest block
        starting_block = app.node.latest_block
        if starting_block is None:
            self._results_body = "Node has no blocks yet."
            self.elements = []
            return

        try:
            results = bloom_search_tx(
                astreum_node=app.node,
                tx_hash=tx_hash_bytes,
                sender=sender_bytes,
                receiver=recipient_bytes,
                key=b"",
                starting_block=starting_block,
                end_block_height=0,
                limit=20,
            )
        except Exception as exc:
            app.flash_message = f"Search error: {exc}"
            return

        if not results:
            self._results_body = "No matching transactions found."
        else:
            lines: list[str] = []
            for tx in results:
                tx_hash_short = (tx.atom_hash or tx.hash or b"").hex()[:16]
                block_short = (tx.block_hash or b"").hex()[:16]
                sender_short = tx.sender.hex()[:16]
                recv_short = tx.recipient.hex()[:16]
                lines.append(
                    f"  TX: 0x{tx_hash_short}..."
                )
                lines.append(
                    f"  S:0x{sender_short}...  ->  R:0x{recv_short}..."
                )
                lines.append(
                    f"  amt={tx.amount}  code={tx.code.name if hasattr(tx.code, 'name') else tx.code}"
                )
                lines.append(f"  block=0x{block_short}...")
                lines.append("")
            self._results_body = "\n".join(lines).rstrip()

        self.elements = []
