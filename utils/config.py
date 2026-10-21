import json
import logging
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric import ed25519


SETTINGS_FILE_NAME = "settings.json"
LATEST_BLOCK_HASH_FILE_NAME = "latest_block_hash.bin"
REDACTED = "<redacted>"


def redact_config(node_config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the node settings with secret values masked.

    Args:
        node_config: Node settings. A key whose name contains "secret" is masked.

    Returns:
        A new dict. The input dict is not changed.
    """
    return {
        key: REDACTED if "secret" in str(key).lower() and value is not None else value
        for key, value in node_config.items()
    }


def redact_args(args: list[str]) -> list[str]:
    """Return a copy of the arguments with secret option values masked.

    Handles `--option value` and `--option=value`. An option is secret when
    its name contains "secret".

    Args:
        args: Command-line arguments.

    Returns:
        A new list. The input list is not changed.
    """
    result: list[str] = []
    mask_next = False
    for token in args:
        if mask_next and not token.startswith("--"):
            result.append(REDACTED)
            mask_next = False
            continue
        mask_next = False
        if token.startswith("--"):
            name, sep, _ = token.partition("=")
            if "secret" in name.lower():
                if sep:
                    result.append(f"{name}={REDACTED}")
                else:
                    result.append(token)
                    mask_next = True
                continue
        result.append(token)
    return result


def load_config(data_dir: Path) -> dict[str, Any]:
    """Load the app configuration stored in `settings.json` if present."""
    config = {}

    settings_path = data_dir / SETTINGS_FILE_NAME
    if settings_path.exists():
        config = json.loads(settings_path.read_text(encoding="utf-8"))
    
    top_configs = ["cli", "node"]

    for k in top_configs:
        if k not in config:
            config[k] = {}

    default_cli_configs = {
        "api_host": "127.0.0.1",
        "api_port": 52781,
        "on_startup_connect_node": True,
        "on_startup_validate_blockchain": True,
        "on_startup_verify_blockchain": False,
        "latest_block_hash_poll_interval": 10.0,
    }
    
    for k, v in default_cli_configs.items():
        if k not in config["cli"]:
            config["cli"][k] = v

    default_node_configs = {
        # "validation_secret_key": None,
        "cold_storage_path": str(data_dir / "storage"),
    }

    for k, v in default_node_configs.items():
        if k not in config["node"]:
            config["node"][k] = v

    if "latest_block_hash" in config["node"]:
        config["node"].pop("latest_block_hash", None)

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
    secret_hex = node_config.get("validation_secret_key_str")
    if not secret_hex:
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


def load_or_create_storage_key(data_dir: Path) -> str:
    """Return the node storage key as hex, creating the key file if missing.

    The file is `accounts/storage.txt` in `data_dir`, in the format `0x` + hex.

    Raises:
        ValueError: If the file exists and does not hold a 32-byte hex key.
    """
    path = data_dir / "accounts" / "storage.txt"
    if path.exists():
        raw = path.read_text().strip().removeprefix("0x")
        try:
            if len(bytes.fromhex(raw)) != 32:
                raise ValueError
        except ValueError:
            raise ValueError(f"{path} does not hold a 32-byte hex key") from None
        return raw

    key = ed25519.Ed25519PrivateKey.generate()
    raw = key.private_bytes_raw().hex()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0x" + raw)
    return raw


def build_node_config(configs: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    """Return a copy of the node settings for passing to `Node`.

    The lib changes the dict it receives in place and adds key objects.
    A copy keeps `configs` free of those values.
    """
    node_config = dict(configs["node"])
    if not node_config.get("storage_secret_key"):
        node_config["storage_secret_key"] = load_or_create_storage_key(data_dir)
    latest_hash = load_node_latest_block_hash(data_dir)
    if latest_hash is not None:
        node_config["latest_block_hash"] = f"0x{latest_hash.hex()}"
    return node_config


def persist_node_latest_block_hash(
    data_dir: Path,
    latest_block_hash: bytes,
    logger: Optional[logging.Logger] = None,
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
    if logger is not None:
        hash_hex = None
        if isinstance(latest_block_hash, (bytes, bytearray)):
            hash_hex = latest_block_hash.hex()
        else:
            try:
                hash_hex = bytes(latest_block_hash).hex()
            except Exception:
                hash_hex = None
        if hash_hex is None:
            logger.info("Saved latest_block_hash to %s", state_path)
        else:
            logger.info("Saved latest_block_hash to %s (0x%s)", state_path, hash_hex)
