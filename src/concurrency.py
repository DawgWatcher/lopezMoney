"""Concurrency infrastructure for Phase 3 write tools.

Provides:
- LockFile context manager with stale-lock detection and fcntl guarantee
- ConcurrentModificationError / LockAcquisitionError exceptions
- identity_tuple helper for optimistic locking
"""

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from src.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

LOCK_PATH = PROJECT_ROOT / ".lock"
LOCK_TIMEOUT_SECONDS = 60


class LockAcquisitionError(RuntimeError):
    """Raised when a lockfile cannot be acquired."""


class ConcurrentModificationError(RuntimeError):
    """Raised when a row was modified during a write operation."""


def identity_tuple(row: dict) -> tuple[str, str, str]:
    """Return (Transaction ID, Date, Amount) from a row dict.

    Raises KeyError if any of those fields are missing.
    """
    return (row["Transaction ID"], row["Date"], row["Amount"])


class LockFile:
    """Context manager for file-based locking with stale detection.

    Uses a JSON blob on disk ({pid, acquired_at}) as the primary gate,
    plus fcntl.flock for a kernel-level guarantee against inter-process races.
    """

    def __init__(self, path: Path | None = None):
        self._path = path or LOCK_PATH
        self._fd = None

    def __enter__(self):
        # Timestamp-based check (primary gate)
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                acquired_at = datetime.fromisoformat(data["acquired_at"])
                age = (datetime.now(timezone.utc) - acquired_at).total_seconds()
                if age < LOCK_TIMEOUT_SECONDS:
                    raise LockAcquisitionError(
                        "Another write is in progress; retry shortly"
                    )
                logger.warning(
                    "Stale lockfile (age=%.0fs) — forcibly overwriting", age
                )
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt lockfile — overwriting")

        # Create/overwrite the file and acquire kernel lock
        self._fd = open(self._path, "w")
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fd.close()
            self._fd = None
            raise LockAcquisitionError(
                "Another write is in progress; retry shortly"
            )

        blob = {
            "pid": os.getpid(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        self._fd.write(json.dumps(blob))
        self._fd.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
        try:
            self._path.unlink(missing_ok=True)
        except Exception:
            pass
        return False
