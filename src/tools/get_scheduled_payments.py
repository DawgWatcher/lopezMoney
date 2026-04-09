"""get_scheduled_payments tool — future-dated rows from Transactions."""

import logging
from datetime import date, datetime

from src.sheets_client import read_all_rows

logger = logging.getLogger(__name__)

_DATE_FORMATS = ["%m/%d/%Y", "%m/%d/%y"]


def _parse_tiller_date(raw: str) -> date | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def get_scheduled_payments() -> list[dict]:
    """Return transactions whose date is in the future.

    If Tiller has no future-dated rows, returns [] and logs a warning.
    """
    today = date.today()
    rows = read_all_rows("Transactions")

    future = []
    for row in rows:
        d = _parse_tiller_date(row.get("Date", ""))
        if d is not None and d > today:
            future.append(row)

    if not future:
        logger.warning(
            "No future-dated transactions found. Tiller may not support "
            "scheduled/future-dated entries in this sheet."
        )

    # Most recent first
    future.sort(
        key=lambda r: _parse_tiller_date(r.get("Date", "")) or today,
        reverse=True,
    )
    return future
