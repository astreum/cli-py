import json
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric import ed25519


SETTINGS_FILE_NAME = "settings.json"
LATEST_BLOCK_HASH_FILE_NAME = "latest_block_hash.bin"


def load_config(data_dir: Path) -> dict[str, Any]:
    """Load or create the app configuration stored in `settings.json`."""
    config = {}

    settings_path = data_dir / SETTINGS_FILE_NAME
    if settings_path.exists():
        config = json.loads(settings_path.read_text(encoding="utf-8"))
    
    top_configs = ["cli", "node"]

    for k in top_configs:
        if k not in config:
            config[k] = {}

    default_cli_configs = {
        "serve_api": False,
        "on_startup_connect_node": False,
        "on_startup_validate_blockchain": False,
        "latest_block_hash_poll_interval": 10.0,
    }
    
    for k, v in default_cli_configs.items():
        if k not in config["cli"]:
            config["cli"][k] = v

    default_node_configs = {
        "verbose": True,
        # "validation_secret_key": None,
        "cold_storage_path": str(data_dir / "atoms"),
    }

    for k, v in default_node_configs.items():
        if k not in config["node"]:
            config["node"][k] = v

    if "latest_block_hash" in config["node"]:
        config["node"].pop("latest_block_hash", None)

    save_config(data_dir, config)

    return config


def save_config(data_dir: Path, config: dict[str, Any]) -> None:
    """Persist the configuration to disk."""
    settings_path = data_dir / SETTINGS_FILE_NAME
    settings_path.write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_validator_private_key(
    configs: dict[str, Any],
) -> tuple[Optional[ed25519.Ed25519PrivateKey], Optional[str]]:
    """Load the validator secret key from config, returning an error on failure."""
    node_config = configs.get("node", {})
    secret_hex = node_config.get("validation_secret_key")
    if not secret_hex:
        return None, "validation secret key is not configured"

    try:
        secret_bytes = bytes.fromhex(secret_hex)
    except ValueError:
        return None, "validation secret key is not valid hex"

    try:
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(secret_bytes)
    except ValueError:
        return None, "validation secret key is not a valid Ed25519 key"

    return private_key, None


def load_node_latest_block_hash(data_dir: Path) -> Optional[bytes]:
    """Load the latest block hash from the local state file if available."""
    state_path = data_dir / LATEST_BLOCK_HASH_FILE_NAME
    if not state_path.exists():
        return None
    data = state_path.read_bytes()
    if not data:
        return None
    return data


def persist_node_latest_block_hash(
    data_dir: Path,
    latest_block_hash: bytes,
) -> None:
    """Persist the latest block hash to the local state file."""
    state_path = data_dir / LATEST_BLOCK_HASH_FILE_NAME
    if state_path.exists():
        try:
            if state_path.read_bytes() == latest_block_hash:
                return
        except OSError:
            pass

    tmp_path = state_path.with_name(f"{LATEST_BLOCK_HASH_FILE_NAME}.tmp")
    tmp_path.write_bytes(latest_block_hash)
    tmp_path.replace(state_path)
