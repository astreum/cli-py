import csv
import dataclasses
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from astreum import find_transactions, get_receipt
from astreum.consensus.models.receipt import STATUS_SUCCESS
from astreum.consensus.transaction import TransactionCode
from astreum.crypto.bloom_search.block_search import find_block_by_height


SENT_FILE_NAME = "sent_transactions.csv"
TRACKED_FILE_NAME = "tracked_transactions.csv"
MAX_CHECKS_PER_PASS = 50
STOP_TIMEOUT = 2.0

SENT_HEADER = "tx_hash,sender,recipient,code,sent_height,sent_time"
TRACKED_HEADER = (
    "tx_hash,sender,recipient,code,sent_height,result,block_hash,"
    "transaction_fee,data_fee,storage_fee,mint"
)
RESULT_SUCCESS = "success"
RESULT_FAILED = "failed"
RESULT_NOT_INCLUDED = "not_included"
_RESULTS = (RESULT_SUCCESS, RESULT_FAILED, RESULT_NOT_INCLUDED)
_CLAIM_CODE = int(TransactionCode.STORAGE_PAYMENT)


@dataclass
class ClaimStats:
    """Lifetime totals of the storage claims that this node sent."""

    sent: int = 0
    succeeded: int = 0
    failed: int = 0
    not_included: int = 0
    earned: int = 0
    fees: int = 0

    @property
    def waiting(self) -> int:
        return self.sent - self.succeeded - self.failed - self.not_included

    @property
    def net(self) -> int:
        return self.earned - self.fees


class _SentRow(NamedTuple):
    tx_hash: str
    sender: str
    recipient: str
    code: int
    sent_height: int


class _Result(NamedTuple):
    result: str
    block_hash: str
    transaction_fee: int
    data_fee: int
    storage_fee: int
    mint: int


_NOT_INCLUDED = _Result(RESULT_NOT_INCLUDED, "", 0, 0, 0, 0)


def _parse_hash(value: str) -> str:
    if len(bytes.fromhex(value)) != 32:
        raise ValueError("not a 32-byte hex hash")
    return value


class TransactionTracker:
    """Check each sent transaction once, after its fee window has closed.

    Reads `sent_transactions.csv` (written by the lib) and appends one result
    line per transaction to `tracked_transactions.csv`. The tracked file is
    the record: at start the tracker reads it, so a restart checks nothing
    twice and counts nothing twice.

    Raises:
        OSError: At construction, when an existing file cannot be read.
    """

    def __init__(self, node, data_dir: Path) -> None:
        self._node = node
        self._sent_path = Path(data_dir) / SENT_FILE_NAME
        self._tracked_path = Path(data_dir) / TRACKED_FILE_NAME
        key = getattr(getattr(node, "config", None), "storage_public_key_bytes", None)
        if not isinstance(key, (bytes, bytearray)):
            key = getattr(node, "storage_public_key_bytes", None)
        self._claim_sender = key.hex() if isinstance(key, (bytes, bytearray)) else None
        self._lock = threading.Lock()
        self._stats = ClaimStats()
        self._sent_offset = 0
        self._seen: set[str] = set()
        self._checked: set[str] = set()
        self._pending: dict[str, _SentRow] = {}
        self._tracked_needs_newline = False
        self._load_tracked()
        self._read_sent()

    def stats(self) -> ClaimStats:
        with self._lock:
            return dataclasses.replace(self._stats)

    def check_due(self, stop_event: Optional[threading.Event] = None) -> int:
        """Check the sent transactions whose window has closed.

        Returns:
            The number of result lines written in this pass.
        """
        head = getattr(self._node, "latest_block", None)
        if head is None:
            return 0
        try:
            self._read_sent()
        except OSError as exc:
            self._warn("Transaction tracker cannot read %s: %s", self._sent_path, exc)
        window = int(self._node.config.storage_claim_fee_window)
        height = int(head.height)
        checks = 0
        written = 0
        for row in list(self._pending.values()):
            if checks >= MAX_CHECKS_PER_PASS:
                break
            if stop_event is not None and stop_event.is_set():
                break
            if height < row.sent_height + window:
                continue
            checks += 1
            result = self._resolve(row, window, head)
            if result is not None and self._append(row, result):
                written += 1
            elif row.tx_hash in self._pending:
                # Move a failed row to the end, so rows that keep failing
                # cannot use the whole pass budget every time.
                self._pending[row.tx_hash] = self._pending.pop(row.tx_hash)
        return written

    def _is_claim(self, sender: str, code: int) -> bool:
        return code == _CLAIM_CODE and sender == self._claim_sender

    def _warn(self, message: str, *args) -> None:
        logger = getattr(self._node, "logger", None)
        if logger is not None:
            logger.warning(message, *args)

    def _load_tracked(self) -> None:
        if not self._tracked_path.exists():
            return
        data = self._tracked_path.read_bytes()
        self._tracked_needs_newline = bool(data) and not data.endswith(b"\n")
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            if not line or line == TRACKED_HEADER:
                continue
            try:
                fields = next(csv.reader([line]))
                if len(fields) != 11 or fields[5] not in _RESULTS:
                    raise ValueError("unexpected fields")
                tx_hash = _parse_hash(fields[0])
                code = int(fields[3])
                fees = int(fields[7]) + int(fields[8]) + int(fields[9])
                mint = int(fields[10])
            except (ValueError, StopIteration):
                self._warn("Skipped malformed line %d in %s", number, self._tracked_path)
                continue
            if tx_hash in self._checked:
                continue
            self._checked.add(tx_hash)
            if self._is_claim(fields[1], code):
                self._count_result(fields[5], fees, mint)

    def _read_sent(self) -> None:
        try:
            with open(self._sent_path, "rb") as f:
                f.seek(self._sent_offset)
                data = f.read()
        except FileNotFoundError:
            return
        end = data.rfind(b"\n")
        if end < 0:
            return
        self._sent_offset += end + 1
        for raw in data[: end + 1].splitlines():
            line = raw.decode("utf-8", errors="replace")
            if not line or line == SENT_HEADER:
                continue
            try:
                fields = next(csv.reader([line]))
                if len(fields) != 6:
                    raise ValueError("unexpected fields")
                row = _SentRow(
                    _parse_hash(fields[0]), fields[1], fields[2], int(fields[3]), int(fields[4])
                )
            except (ValueError, StopIteration):
                self._warn("Skipped malformed line in %s: %r", self._sent_path, line[:80])
                continue
            if row.tx_hash in self._seen:
                continue
            self._seen.add(row.tx_hash)
            if self._is_claim(row.sender, row.code):
                with self._lock:
                    self._stats.sent += 1
            if row.tx_hash not in self._checked:
                self._pending[row.tx_hash] = row

    def _resolve(self, row: _SentRow, window: int, head) -> Optional[_Result]:
        tx_hash = bytes.fromhex(row.tx_hash)
        try:
            found = find_transactions(
                self._node,
                tx_hash=tx_hash,
                start_height=row.sent_height + window,
                end_height=row.sent_height,
                limit=1,
            )
            if not found:
                # The lib also returns no transactions when it cannot load a
                # block of the range, so "not included" needs the range end.
                reached = find_block_by_height(
                    self._node, starting_block=head, target_height=row.sent_height
                )
                if reached is None:
                    self._warn("Blocks of %s are not available yet", row.tx_hash[:16])
                    return None
                return _NOT_INCLUDED
            block_hash = found[0].block_hash
            receipt = get_receipt(self._node, block_hash, tx_hash)
            if receipt is None:
                self._warn("Receipt of %s is not available yet", row.tx_hash[:16])
                return None
            return _Result(
                RESULT_SUCCESS if receipt.status == STATUS_SUCCESS else RESULT_FAILED,
                block_hash.hex(),
                int(receipt.transaction_fee),
                int(receipt.data_fee),
                int(receipt.storage_fee),
                int(receipt.mint),
            )
        except Exception as exc:
            self._warn("Check of %s failed: %s: %s", row.tx_hash[:16], type(exc).__name__, exc)
            return None

    def _append(self, row: _SentRow, result: _Result) -> bool:
        line = ",".join(
            str(value)
            for value in (
                row.tx_hash,
                row.sender,
                row.recipient,
                row.code,
                row.sent_height,
                *result,
            )
        ) + "\n"
        try:
            with open(self._tracked_path, "a", encoding="utf-8", newline="") as f:
                if f.tell() == 0:
                    line = TRACKED_HEADER + "\n" + line
                elif self._tracked_needs_newline:
                    line = "\n" + line
                f.write(line)
        except OSError as exc:
            self._warn("Transaction tracker cannot write %s: %s", self._tracked_path, exc)
            return False
        self._tracked_needs_newline = False
        self._checked.add(row.tx_hash)
        self._pending.pop(row.tx_hash, None)
        if self._is_claim(row.sender, row.code):
            fees = result.transaction_fee + result.data_fee + result.storage_fee
            self._count_result(result.result, fees, result.mint)
        return True

    def _count_result(self, result: str, fees: int, mint: int) -> None:
        with self._lock:
            if result == RESULT_SUCCESS:
                self._stats.succeeded += 1
                self._stats.earned += mint
                self._stats.fees += fees
            elif result == RESULT_FAILED:
                self._stats.failed += 1
                self._stats.fees += fees
            else:
                self._stats.not_included += 1


def start_transaction_tracker(
    *,
    node,
    data_dir: Path,
    poll_interval: float,
) -> tuple[TransactionTracker, Callable[[], None]]:
    """Start a daemon thread that runs `check_due` every `poll_interval` seconds.

    Returns:
        The tracker and a function that stops the thread. The stop function
        waits at most `STOP_TIMEOUT` seconds for the thread to end; a check
        that is still running ends with the process and runs again later.

    Raises:
        OSError: The tracker cannot read its files. No thread is started.
    """
    tracker = TransactionTracker(node, data_dir)
    stop_event = threading.Event()
    interval = max(poll_interval, 0.01)

    def _run() -> None:
        while not stop_event.is_set():
            try:
                tracker.check_due(stop_event)
            except Exception as exc:
                logger = getattr(node, "logger", None)
                if logger is not None:
                    logger.warning(
                        "Transaction tracker pass failed: %s: %s", type(exc).__name__, exc
                    )
            stop_event.wait(interval)

    thread = threading.Thread(target=_run, name="tx-tracker", daemon=True)
    thread.start()

    def _stop() -> None:
        stop_event.set()
        thread.join(timeout=min(interval * 2, STOP_TIMEOUT))

    return tracker, _stop
