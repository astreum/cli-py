from __future__ import annotations

import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .base import BasePage
from .element import PageElement


class SettingsPage(BasePage):
    NODE_INFO_INDEX = 0
    ACCOUNT_INPUT_INDEX = 1

    def __init__(self) -> None:
        super().__init__(title="Settings")

    def load_elements(self, app: "App", *args, **kwargs):
        if self.elements == []:
            default_account = self._default_account_from_config(app)
            self.elements = [
                PageElement(label="Node"),
                PageElement(label="Validation Account Name", input=[default_account]),
                PageElement(label="Save Validation Key", action=self._handle_validator_save),
                PageElement(label="Delete Validation Key", action=self._handle_delete),
            ]

    def _default_account_from_config(self, app: "App") -> str:
        node_config = app.configs["node"]
        secret_hex = node_config.get("validator_secret_key")
        if not secret_hex:
            return ""

        try:
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(secret_hex))
        except ValueError:
            return ""

        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return f"0x{public_key_bytes.hex()}"

    def _handle_validator_save(self, app: "App") -> None:
        account_element = self.elements[self.ACCOUNT_INPUT_INDEX]
        account_name = account_element.input[0] if account_element.input else ""
        account_name = account_name.strip()
        if not account_name:
            app.flash_message = "Enter the name of an account stored under accounts/."
            return

        accounts_dir = app.data_dir / "accounts"
        account_path = accounts_dir / f"{account_name}.bin"
        if not account_path.exists():
            app.flash_message = f"Account '{account_name}' not found."
            return

        try:
            private_bytes = account_path.read_bytes()
        except OSError as exc:
            app.flash_message = f"Failed to read account '{account_name}': {exc}"
            return

        try:
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        except ValueError:
            app.flash_message = "Account file does not contain a valid Ed25519 key."
            return

        storage_name = account_path.stem
        configs = app.configs
        configs["node"]["validation_secret_key"] = private_bytes.hex()

        settings_path = app.data_dir / "settings.json"
        try:
            settings_path.write_text(
                json.dumps(configs, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            app.flash_message = f"Failed to update settings: {exc}"
            return

        app.node.validation_secret_key = private_key
        input_element = self.elements[self.ACCOUNT_INPUT_INDEX]
        input_element.input = [storage_name]
        input_element.input_index = (0, len(storage_name))

        app.flash_message = f"Validator key saved from account '{storage_name}'."

        self.elements = []

    def _handle_delete(self, app: "App") -> None:
        node_config = app.configs["node"]
        if "validation_secret_key" not in node_config:
            app.flash_message = "No validator key is configured."
            return

        node_config.pop("validation_secret_key", None)
        node_config.pop("validation_account", None)

        settings_path = app.data_dir / "settings.json"
        try:
            settings_path.write_text(
                json.dumps(app.configs, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            app.flash_message = f"Failed to update settings: {exc}"
            return

        node = app.node
        node.validation_secret_key = None
        input_element = self.elements[self.ACCOUNT_INPUT_INDEX]
        input_element.input = [""]
        input_element.input_index = (0, 0)

        app.flash_message = "Validator key removed."

        self.elements = []
