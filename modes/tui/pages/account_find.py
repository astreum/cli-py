from __future__ import annotations

from ..base import BasePage
from ..element import PageElement

from astreum.validation.models.block import Block
from astreum.validation.models.accounts import Accounts
from astreum.machine.models.expression import ZERO32


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
            app.flash_message = "Address is required."
            return

        # Validate chain ID
        try:
            chain_id = int(chain_id_str)
        except ValueError:
            app.flash_message = "Chain ID must be an integer."
            return

        node_chain_id = app.node.config.get("chain_id")
        if node_chain_id is not None and chain_id != node_chain_id:
            app.flash_message = (
                f"Node is not tracking chain {chain_id} "
                f"(configured chain_id={node_chain_id})"
            )
            return

        # Parse address
        try:
            address_bytes = bytes.fromhex(address.removeprefix("0x"))
        except ValueError:
            app.flash_message = "Invalid hex in Address."
            return

        # Resolve block
        block = None
        if block_str:
            if block_str.startswith("#"):
                # Resolve by height
                try:
                    target_height = int(block_str[1:])
                except ValueError:
                    app.flash_message = "Invalid block height after #."
                    return
                cur = app.node.latest_block
                while cur is not None and cur.height > target_height:
                    cur = cur.previous_block
                if cur is None or cur.height != target_height:
                    app.flash_message = f"Block at height #{target_height} not found."
                    return
                block = cur
            elif block_str.startswith("0x"):
                # Resolve by hash
                try:
                    block_hash_bytes = bytes.fromhex(block_str[2:])
                except ValueError:
                    app.flash_message = "Invalid hex in block hash."
                    return
                try:
                    block = Block.from_storage(app.node, block_hash_bytes)
                except ValueError:
                    app.flash_message = "Block not found for that hash."
                    return
            else:
                app.flash_message = "Block must start with # (height) or 0x (hash), or be empty for latest."
                return
        else:
            block = app.node.latest_block

        if block is None:
            self._results_body = "Node has no blocks yet."
            self.elements = []
            return

        # Load account
        if block.accounts_hash is None or block.accounts_hash == ZERO32:
            self._results_body = "Block has no accounts."
            self.elements = []
            return

        accounts = Accounts(root_hash=block.accounts_hash)
        try:
            account = accounts.get_account(address_bytes, app.node)
        except Exception as exc:
            app.flash_message = f"Failed to load account: {exc}"
            return

        if account is None:
            self._results_body = "Account not found."
            self.elements = []
            return

        # Format result
        lines = [
            f"  Account at block #{block.height} (0x{(block.atom_hash or b'').hex()[:16]}...)",
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
