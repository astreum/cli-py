"""Account-related helpers for the Astreum CLI."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


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


def _slugify_account_name(name: str) -> str:
    """Convert an account name into a filesystem-friendly slug."""
    cleaned = re.sub(r"\s+", "_", name.strip())
    slug = re.sub(r"[^0-9a-zA-Z_-]+", "_", cleaned)
    slug = slug.strip("_")
    if not slug:
        slug = "account"
    return slug


def create_account(data_dir: Path, name: str) -> tuple[bool, str]:
    """Create a new account file with a freshly generated private key."""
    accounts_dir = data_dir / "accounts"
    slug = _slugify_account_name(name)

    candidate_path = accounts_dir / f"{slug}.bin"
    suffix = 1
    while candidate_path.exists():
        candidate_path = accounts_dir / f"{slug}_{suffix}.bin"
        suffix += 1

    private_key = ed25519.Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    try:
        candidate_path.write_bytes(private_bytes)
    except OSError as exc:
        return False, f"Failed to save account: {exc}"

    display_name = candidate_path.stem
    return True, f"Created account '{display_name}'."
