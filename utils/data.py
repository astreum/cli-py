import os
from pathlib import Path
import platform


def ensure_data_dir() -> Path:
    """Ensure the data directory structure exists and return its path."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / "Astreum" / "cli-py"
    target.mkdir(parents=True, exist_ok=True)
    for folder in ("accounts", "atoms"):
        (target / folder).mkdir(exist_ok=True)
    return target