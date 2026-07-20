from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

import uvicorn

from astreum import Node
from astreum.communication.node import connect_node
from utils.config import persist_node_latest_block_hash, load_validator_private_key
from utils.forks import load_node_forks, persist_node_forks
from utils.latest_block import start_latest_block_hash_poller


def run_headless(
    *,
    data_dir: Path,
    configs: dict[str, Any],
    node: Node,
    api_host: Optional[str] = None,
    api_port: Optional[int] = None,
) -> int:
    """Run the CLI in headless mode without launching the TUI.

    If *api_port* is set (via CLI flag or config file), starts an HTTP API
    server on a daemon thread alongside the headless lifecycle.
    """
    should_connect = configs["cli"]["on_startup_connect_node"]
    validate_blockchain = configs["cli"]["on_startup_validate_blockchain"]
    verify_blockchain = configs["cli"]["on_startup_verify_blockchain"]

    # Resolve API host/port from CLI arg → config file default
    api_host = api_host or configs["cli"].get("api_host")
    api_port = api_port or configs["cli"].get("api_port")
    serve_api = api_port is not None

    wait_for_disconnect = False
    stop_latest_block_hash_poller_fn = None
    try:
        if should_connect:
            sys.stdout.write("connecting node...\n")
            sys.stdout.flush()
            try:
                connect_node(node)
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

        if verify_blockchain:
            sys.stdout.write("verifying blockchain...\n")
            sys.stdout.flush()
            try:
                node.verify()
                sys.stdout.write("blockchain verification started\n")
                sys.stdout.flush()
                wait_for_disconnect = True
            except Exception as exc:  # pragma: no cover - best effort logging
                sys.stdout.write(f"blockchain verification failed: {exc}\n")
                sys.stdout.flush()

        load_node_forks(data_dir=data_dir, node=node)

        poll_interval = configs["cli"]["latest_block_hash_poll_interval"]
        stop_latest_block_hash_poller_fn = start_latest_block_hash_poller(
            node=node,
            data_dir=data_dir,
            poll_interval=poll_interval,
        )

        # --- Start API server (if requested) ---
        if serve_api:
            from modes.api.server import set_node, app

            # Use config host as fallback if CLI flag wasn't given
            api_host = api_host or configs["cli"].get("api_host", "127.0.0.1")
            set_node(node)

            sys.stdout.write(f"starting API server on {api_host}:{api_port}\n")
            sys.stdout.flush()

            server_thread = threading.Thread(
                target=uvicorn.run,
                kwargs={
                    "app": app,
                    "host": api_host,
                    "port": api_port,
                    "log_level": "warning",
                },
                daemon=True,
                name="astreum-api",
            )
            server_thread.start()

    finally:
        if wait_for_disconnect:
            _wait_until_node_disconnects(node)
        if stop_latest_block_hash_poller_fn is not None:
            stop_latest_block_hash_poller_fn()
        latest_hash = node.latest_block_hash
        if latest_hash is not None:
            persist_node_latest_block_hash(
                data_dir=data_dir,
                latest_block_hash=latest_hash,
                logger=node.logger,
            )
        persist_node_forks(data_dir=data_dir, node=node)

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
