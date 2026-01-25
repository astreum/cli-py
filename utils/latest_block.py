import threading
import time
from pathlib import Path
from typing import Optional, Callable

from utils.config import persist_node_latest_block_hash
from utils.forks import persist_node_forks


def start_latest_block_hash_poller(
    *,
    node,
    data_dir: Path,
    poll_interval: float,
) -> Callable[[], None]:
    """
    Start a background thread that persists the latest block hash when it changes.

    Returns a callable to stop the poller; it waits for thread exit when invoked.
    """
    stop_event = threading.Event()

    def _poll() -> None:
        last_written: Optional[bytes] = None
        minimum_interval = 0.05
        interval = max(poll_interval, minimum_interval)
        logger = node.logger
        while not stop_event.is_set():
            try:
                current = getattr(node, "latest_block_hash", None)
                if current and current != last_written:
                    persist_node_latest_block_hash(
                        data_dir=data_dir,
                        latest_block_hash=current,
                        logger=logger,
                    )
                    persist_node_forks(data_dir=data_dir, node=node)
                    last_written = current
            except Exception:
                # best-effort; continue polling
                pass
            stop_event.wait(interval)

    thread = threading.Thread(target=_poll, name="latest-block-hash-poller", daemon=True)
    thread.start()

    def _stop() -> None:
        stop_event.set()
        thread.join(timeout=poll_interval * 2 if poll_interval > 0 else 0.5)

    return _stop
