import json
import os
import platform
from pathlib import Path
from typing import Any


def ensure_data_dir() -> Path:
    """Ensure the data directory structure exists and return its path."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / "Astreum" / "cli-py"
    target.mkdir(parents=True, exist_ok=True)
    for folder in ("accounts", "definitions", "atoms"):
        (target / folder).mkdir(exist_ok=True)
    return target


def load_config(data_dir: Path) -> dict[str, Any]:
    """Load or create the app configuration stored in `settings.json`."""
    config = {}

    settings_path = data_dir / "settings.json"
    if settings_path.exists():
        config = json.loads(settings_path.read_text(encoding="utf-8"))
    
    top_configs = ["cli", "node"]

    for k in top_configs:
        if k not in config:
            config[k] = {}

    default_cli_configs = {
        "serve_api": False
    }
    
    for k, v in default_cli_configs.items():
        if k not in config["cli"]:
            config["cli"][k] = v

    default_node_configs = {
        "validation_secret_key": None,
        "cold_storage_path": str(data_dir / "atoms"),
    }

    for k, v in default_node_configs.items():
        if k not in config["node"]:
            config["node"][k] = v

    settings_path.write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return config
