from __future__ import annotations

from ..base import BasePage
from ..element import PageElement

from astreum.consensus.block.encoding.decode import get_block_from_storage
from astreum.consensus.block.holders import block_holder
from astreum.crypto.bloom_search.block_search import find_block_by_height
from astreum.expression import ZERO32


class AccountSearchPage(BasePage):
    def __init__(self):
        super().__init__(title="Find Account")
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
        address_val = self._input("Address")
        chain_id_val = self._input("Chain ID") or "0"
        block_val = self._input("Block")

        self.elements = [
            PageElement(label="Filter"),
            PageElement(label="Address", input=[address_val]),
            PageElement(label="Chain ID", input=[chain_id_val]),
            PageElement(label="Block (#height/0xhash)", input=[block_val]),
            PageElement(label="[Find]", action=self._do_find),
            PageElement(label="Results"),
            PageElement(label="", body=self._results_body),
        ]

    def _do_find(self, app):
        # Save inputs
        for el in self.elements:
            if el.input and el.input[0]:
                self._saved_inputs[el.label] = el.input[0]

        address = self._input("Address")
        chain_id_str = self._input("Chain ID") or "0"
        block_str = self._input("Block")

        if not address:
            app.flash("Address is required.", "error")
            return

        # Validate chain ID
        try:
            chain_id = int(chain_id_str)
        except ValueError:
            app.flash("Chain ID must be an integer.", "error")
            return

        node_chain_id = app.node.config.chain_id
        if node_chain_id is not None and chain_id != node_chain_id:
            app.flash(
                f"Node is not tracking chain {chain_id} "
                f"(configured chain_id={node_chain_id})",
                "error",
            )
            return

        # Parse address
        try:
            address_bytes = bytes.fromhex(address.removeprefix("0x"))
        except ValueError:
            app.flash("Invalid hex in Address.", "error")
            return

        # Resolve block
        block = None
        if block_str:
            if block_str.startswith("#"):
                # Resolve by height
                try:
                    target_height = int(block_str[1:])
                except ValueError:
                    app.flash("Invalid block height after #.", "error")
                    return
                head_hash = app.node.latest_block_hash
                if head_hash is None:
                    app.flash("Node has no blocks yet.", "info")
                    return
                try:
                    start = get_block_from_storage(
                        app.node, head_hash, contact=block_holder(app.node, head_hash)
                    )
                except Exception:
                    app.flash("Latest block not loaded yet.", "info")
                    return
                try:
                    block = find_block_by_height(
                        app.node,
                        starting_block=start,
                        target_height=target_height,
                    )
                except Exception as exc:
                    app.flash(f"Lookup failed: {exc}", "error")
                    return
                if block is None:
                    app.flash(f"Block at height #{target_height} not found.", "error")
                    return
            elif block_str.startswith("0x"):
                # Resolve by hash
                try:
                    block_hash_bytes = bytes.fromhex(block_str[2:])
                except ValueError:
                    app.flash("Invalid hex in block hash.", "error")
                    return
                try:
                    block = get_block_from_storage(app.node, block_hash_bytes)
                except ValueError:
                    app.flash("Block not found for that hash.", "error")
                    return
            else:
                app.flash("Block must start with # (height) or 0x (hash), or be empty for latest.", "error")
                return
        else:
            head_hash = app.node.latest_block_hash
            if head_hash is not None:
                try:
                    block = get_block_from_storage(
                        app.node, head_hash, contact=block_holder(app.node, head_hash)
                    )
                except Exception:
                    app.flash("Latest block not loaded yet.", "info")
                    return

        if block is None:
            self._results_body = "Node has no blocks yet."
            self.elements = []
            return

        # Load account
        if block.accounts_hash is None or block.accounts_hash == ZERO32:
            self._results_body = "Block has no accounts."
            self.elements = []
            return

        accounts = block.accounts
        if accounts is None:
            self._results_body = "Block has no accounts."
            self.elements = []
            return

        try:
            account = accounts.get_account(address_bytes, app.node)
        except Exception as exc:
            app.flash(f"Failed to load account: {exc}", "error")
            return

        if account is None:
            self._results_body = "Account not found."
            self.elements = []
            return

        # Format result
        lines = [
            f"  Account at block #{block.height} (0x{(block.expr_id or b'').hex()[:16]}...)",
            f"  Chain ID: {block.chain_id}",
            "",
            f"  Balance:   {account.balance}",
            f"  Counter:   {account.counter}",
            f"  Code Hash: 0x{account.code_hash.hex()[:32]}...",
            f"  Data Hash: 0x{account.data_hash.hex()[:32]}...",
            f"  Channels:  0x{account.channels_hash.hex()[:32]}...",
        ]
        self._results_body = "\n".join(lines)

        self.elements = []
