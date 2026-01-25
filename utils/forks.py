from pathlib import Path
from typing import Any

from astreum.consensus.fork.node import export_forks, import_forks

FORKS_FILE_NAME = "forks.bin"


def load_node_forks(data_dir: Path, node: Any) -> None:
    forks_path = data_dir / FORKS_FILE_NAME
    if forks_path.exists():
        payload = forks_path.read_bytes()
        import_forks(node, payload)


def persist_node_forks(data_dir: Path, node: Any) -> None:
    forks_path = data_dir / FORKS_FILE_NAME
    payload = export_forks(node)
    tmp_path = forks_path.with_name(f"{FORKS_FILE_NAME}.tmp")
    tmp_path.write_bytes(payload)
    tmp_path.replace(forks_path)
