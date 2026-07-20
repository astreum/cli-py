from __future__ import annotations

from ..base import BasePage
from ..element import PageElement

from astreum.consensus.block.encoding.decode import get_block_from_storage
from astreum.crypto.bloom_search.block_search import find_block_by_height
from astreum.expression import ZERO32


class BlockSearchPage(BasePage):
    def __init__(self):
        super().__init__(title="View Block")
        self._results_body = "Look up a block to see its details."
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
        hash_val = self._input("Hash")
        height_val = self._input("Height")

        self.elements = [
            PageElement(label="Filter"),
            PageElement(label="Hash (0x...)", input=[hash_val]),
            PageElement(label="Height (#...)", input=[height_val]),
            PageElement(label="[Latest]", action=self._do_latest),
            PageElement(label="[Fetch]", action=self._do_fetch),
            PageElement(label="Result"),
            PageElement(label="", body=self._results_body),
        ]

    def _format_block(self, block: Block) -> str:
        def short(b: bytes | None) -> str:
            if not b:
                return "<none>"
            return b.hex()[:16] + "..."

        lines = [
            f"  Height:    #{block.height}",
            f"  Chain ID:  {block.chain_id}",
            f"  Timestamp: {block.timestamp}",
            "",
            f"  Expr ID:    0x{short(block.expr_id)}",
            f"  Prev Hash:  0x{short(block.previous_block_hash)}",
            "",
            f"  Accounts:      0x{short(block.accounts_hash)}",
            f"  Transactions:  0x{short(block.transactions_hash)}",
            f"  Receipts:      0x{short(block.receipts_hash)}",
            "",
            f"  Difficulty: {block.difficulty}",
            f"  Nonce:      {block.nonce}",
            "",
            f"  Cumulative Total Fee:            {block.cumulative_total_fee}",
            f"  Cumulative Stake:                {block.cumulative_stake}",
            f"  Total Mint:                      {block.total_mint}",
            f"  Total Transaction Fee:           {block.total_transaction_fee}",
            f"  Total Storage Fee:               {block.total_storage_fee}",
            "",
            f"  Validator Key: 0x{short(block.validator_public_key_bytes)}",
            f"  Body Hash:     0x{short(block.body_hash)}",
            f"  Signature:     0x{short(block.signature)}",
            f"  Bloom Hash:    0x{short(block.bloom_hash)}",
        ]
        return "\n".join(lines)

    def _do_latest(self, app):
        block = app.node.latest_block
        if block is None:
            self._results_body = "Node has no blocks yet."
            self.elements = []
            return
        self._results_body = self._format_block(block)
        self.elements = []

    def _do_fetch(self, app):
        # Save inputs
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        hash_str = self._input("Hash")
        height_str = self._input("Height")

        if not hash_str and not height_str:
            app.flash_message = "Provide a hash or height."
            return

        try:
            if hash_str:
                # Look up by hash
                raw = hash_str.removeprefix("0x")
                block_hash = bytes.fromhex(raw)
                block = get_block_from_storage(app.node, block_hash)
            else:
                # Look up by height
                target = int(height_str.removeprefix("#"))
                start = app.node.latest_block
                if start is None:
                    self._results_body = "Node has no blocks yet."
                    self.elements = []
                    return
                block = find_block_by_height(
                    app.node,
                    starting_block=start,
                    target_height=target,
                )
        except ValueError as exc:
            app.flash_message = f"Invalid input: {exc}"
            return
        except Exception as exc:
            app.flash_message = f"Lookup failed: {exc}"
            return

        if block is None:
            self._results_body = "Block not found."
            self.elements = []
            return

        self._results_body = self._format_block(block)
        self.elements = []
