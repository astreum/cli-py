from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from astreum import Node
from utils.config import persist_node_latest_block_hash, load_validator_private_key
from utils.latest_block import start_latest_block_hash_poller


def run_headless(
    *,
    data_dir: Path,
    configs: dict[str, Any],
) -> int:
    """Run the CLI in headless mode without launching the TUI."""

    node = Node(config=configs["node"])
    poll_interval = configs["cli"]["latest_block_hash_poll_interval"]
    stop_poller = start_latest_block_hash_poller(
        node=node,
        data_dir=data_dir,
        poll_interval=poll_interval,
    )

    connect_node = configs["cli"]["on_startup_connect_node"]
    validate_blockchain = configs["cli"]["on_startup_validate_blockchain"]

    wait_for_disconnect = False
    try:
        if connect_node:
            sys.stdout.write("connecting node...\n")
            sys.stdout.flush()
            try:
                node.connect()
                sys.stdout.write("node connected\n")
                sys.stdout.flush()
                wait_for_disconnect = True
            except Exception as exc:  # pragma: no cover - best effort logging
                sys.stdout.write(f"node connect failed: {exc}\n")
                sys.stdout.flush()

        if validate_blockchain:
            sys.stdout.write("validating blockchain...\n")
            sys.stdout.flush()
            try:
                validator_key, error = load_validator_private_key(configs)
                if validator_key is None:
                    sys.stdout.write(f"blockchain validation skipped: {error}\n")
                else:
                    node.validate(validator_key)
                    sys.stdout.write("blockchain validation complete\n")
                sys.stdout.flush()
            except Exception as exc:  # pragma: no cover - best effort logging
                sys.stdout.write(f"blockchain validation failed: {exc}\n")
                sys.stdout.flush()
    finally:
        stop_poller()
        if wait_for_disconnect:
            _wait_until_node_disconnects(node)
        latest_hash = node.latest_block_hash
        if latest_hash is not None:
            persist_node_latest_block_hash(
                data_dir=data_dir,
                latest_block_hash=latest_hash,
            )

    return 0


def _wait_until_node_disconnects(node: Node, *, poll_interval: float = 0.5) -> None:
    """Block until the node reports it is disconnected."""
    if not node.is_connected:
        return
    
    minimum_interval = 0.1
    sleep_interval = max(poll_interval, minimum_interval)
    while node.is_connected:
        time.sleep(sleep_interval)
    sys.stdout.write("node disconnected\n")
    sys.stdout.flush()
