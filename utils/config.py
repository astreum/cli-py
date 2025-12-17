import json
import os
import platform
from pathlib import Path
from typing import Any


SETTINGS_FILE_NAME = "settings.json"


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
    }
    
    for k, v in default_cli_configs.items():
        if k not in config["cli"]:
            config["cli"][k] = v

    default_node_configs = {
        "verbose": True,
        # "validation_secret_key": None,
        "cold_storage_path": str(data_dir / "atoms"),
        "latest_block_hash": None,
    }

    for k, v in default_node_configs.items():
        if k not in config["node"]:
            config["node"][k] = v

    save_config(data_dir, config)

    return config


def save_config(data_dir: Path, config: dict[str, Any]) -> None:
    """Persist the configuration to disk."""
    settings_path = data_dir / SETTINGS_FILE_NAME
    settings_path.write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def persist_node_latest_block_hash(
    data_dir: Path,
    configs: dict[str, Any],
    latest_block_hash: bytes,
) -> None:
    """Persist the latest block hash provided to the stored config."""
    hex_value = f"0x{latest_block_hash.hex()}"

    node_configs = configs.setdefault("node", {})
    if node_configs.get("latest_block_hash") == hex_value:
        return

    node_configs["latest_block_hash"] = hex_value
    save_config(data_dir, configs)
