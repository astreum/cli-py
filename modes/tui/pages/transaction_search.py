from __future__ import annotations

import hashlib

from ..base import BasePage
from ..element import PageElement

from astreum.consensus.transaction.from_storage import get_transaction_from_storage
from astreum.crypto.bloom_search import bloom_search_tx


class TransactionSearchPage(BasePage):
    def __init__(self):
        super().__init__(title="Search Transaction")
        self.flag_hash = False
        self.flag_data = False
        self._results_body = "Search for results!"
        self._saved_inputs: dict[str, str] = {}

    def load_elements(self, *args, **kwargs):
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        if self.elements == []:
            self._rebuild()

    def _input(self, label: str) -> str:
        return self._saved_inputs.get(label, "")

    def _rebuild(self):
        tx_hash_val = self._input("Tx Hash")
        id_val = self._input("ID")
        sender_val = self._input("Sender")
        recipient_val = self._input("Recipient")

        flag_hash_label = "flag_hash" + ("  [ON]" if self.flag_hash else "  [OFF]")
        flag_data_label = "flag_data" + ("  [ON]" if self.flag_data else "  [OFF]")

        self.elements = [
            PageElement(label="Tx Hash (0x...)", input=[tx_hash_val]),
            PageElement(label="Filter"),
            PageElement(label="ID", input=[id_val]),
            PageElement(label="Sender", input=[sender_val]),
            PageElement(label="Recipient", input=[recipient_val]),
            PageElement(label=flag_hash_label, action=self._toggle_flag_hash),
            PageElement(label=flag_data_label, action=self._toggle_flag_data),
            PageElement(label="[Search]", action=self._do_search),
            PageElement(label="Results"),
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
        if do_hash:
            return hashlib.sha256(value.encode("utf-8")).digest()
        return bytes.fromhex(value)

    @staticmethod
    def _format_tx(tx) -> str:
        def short(b: bytes | None, n: int = 16) -> str:
            if not b:
                return "<none>"
            return b.hex()[:n] + "..."

        lines = [
            f"  TX: 0x{short(tx.atom_hash)}",
            f"  Sender:    0x{short(tx.sender)}",
            f"  Recipient: 0x{short(tx.recipient)}",
            f"  Amount:    {tx.amount}",
            f"  Chain ID:  {tx.chain_id}",
            f"  Counter:   {tx.counter}",
            f"  Cost:      {tx.cost_limit}",
            f"  Code:      {tx.code.name if hasattr(tx.code, 'name') else tx.code}",
            f"  Version:   {tx.version}",
            f"  Data:      0x{tx.data.hex()[:32] if tx.data else '<none>'}",
            f"  Body Hash: 0x{short(tx.body_hash)}",
            f"  Signature: 0x{short(tx.signature)}",
        ]
        return "\n".join(lines)

    def _do_search(self, app):
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        tx_hash_val = self._input("Tx Hash")
        id_val = self._input("ID")
        sender_val = self._input("Sender")
        recipient_val = self._input("Recipient")

        # Direct hash lookup if only Tx Hash is filled
        if tx_hash_val:
            try:
                tx_bytes = bytes.fromhex(tx_hash_val.removeprefix("0x"))
            except ValueError:
                app.flash_message = "Invalid hex in Tx Hash."
                return

            try:
                tx = get_transaction_from_storage(app.node, tx_bytes)
            except ValueError as exc:
                app.flash_message = f"Transaction not found: {exc}"
                return

            self._results_body = self._format_tx(tx)
            self.elements = []
            return

        # Bloom filter search
        if not any([id_val, sender_val, recipient_val]):
            app.flash_message = "Provide a Tx Hash or at least one filter field (ID, Sender, Recipient)"
            return

        do_hash = self.flag_data
        try:
            tx_hash_bytes = self._hex_or_hash(id_val, do_hash) if id_val else b""
            sender_bytes = self._hex_or_hash(sender_val, do_hash) if sender_val else b""
            recipient_bytes = self._hex_or_hash(recipient_val, do_hash) if recipient_val else b""
        except ValueError:
            app.flash_message = "Invalid hex in input (try toggling flag_data to hash)"
            return

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
                lines.append(f"  TX: 0x{tx_hash_short}...")
                lines.append(f"  S:0x{sender_short}...  ->  R:0x{recv_short}...")
                lines.append(f"  amt={tx.amount}  code={tx.code.name if hasattr(tx.code, 'name') else tx.code}")
                lines.append(f"  block=0x{block_short}...")
                lines.append("")
            self._results_body = "\n".join(lines).rstrip()

        self.elements = []
