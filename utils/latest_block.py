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
        if logger:
            logger.info("Block hash poller started (interval=%ss)", interval)
        while not stop_event.is_set():
            try:
                current = getattr(node, "latest_block_hash", None)
                if current is None:
                    node.latest_block = None
                    if logger:
                        logger.info("Poller: no latest_block_hash yet")
                else:
                    if logger:
                        logger.info("Poller has hash %s", current.hex()[:16])
                    if current != last_written:
                        persist_node_latest_block_hash(
                            data_dir=data_dir,
                            latest_block_hash=current,
                            logger=logger,
                        )
                    try:
                        if logger:
                            logger.debug("Calling Block.from_storage for %s", current.hex()[:16])
                        from astreum.validation.models.block import Block
                        node.latest_block = Block.from_storage(node, current)
                        if logger:
                            logger.debug("Block.from_storage succeeded for %s", current.hex()[:16])
                        if current != last_written:
                            last_written = current
                            try:
                                persist_node_forks(data_dir=data_dir, node=node)
                            except Exception:
                                pass
                    except Exception as exc:
                        node.latest_block = None
                        attempts = getattr(node, "_block_fetch_attempts", 0)
                        node._block_fetch_attempts = attempts + 1
                        if logger:
                            logger.debug(
                                "Block fetch failed for %s (attempt #%s): %s: %s",
                                current.hex()[:16], attempts + 1, type(exc).__name__, exc,
                            )
            except Exception:
                pass
            stop_event.wait(interval)

    thread = threading.Thread(target=_poll, name="latest-block-hash-poller", daemon=True)
    thread.start()

    def _stop() -> None:
        stop_event.set()
        thread.join(timeout=poll_interval * 2 if poll_interval > 0 else 0.5)

    return _stop
