from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from pages.base import BasePage
from pages.element import PageElement


def load_accounts(data_dir: Optional[Path]) -> list[tuple[str, str]]:
    """Return (display_name, short_public_hex) pairs for detected accounts."""
    if data_dir is None:
        return []

    accounts_dir = data_dir / "accounts"
    if not accounts_dir.exists():
        return []

    entries: list[tuple[str, str]] = []
    for account_file in sorted(accounts_dir.glob("*.bin")):
        try:
            private_bytes = account_file.read_bytes()
        except OSError:
            continue
        if len(private_bytes) != 32:
            continue
        try:
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        except ValueError:
            continue

        display_name = account_file.stem
        full_hex = public_bytes.hex()
        entries.append((display_name, full_hex))

    return entries


class AccountListPage(BasePage):
    def __init__(self) -> None:
        super().__init__(title="Account List")

    def load_elements(self, app: "App"):
        if self.elements == []:
            accounts = load_accounts(app.data_dir)
            self.elements = [
                PageElement(label=name, body=pub_hex)
                    for name, pub_hex in accounts
                ]