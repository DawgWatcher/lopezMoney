"""Thin wrapper around the authorized Sheets API client."""

from src.auth import get_sheets_client
from src.config import SHEET_ID

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = get_sheets_client()
    return _client


def read_range(tab: str, cell_range: str | None = None) -> list[list[str]]:
    """Read a range from a tab. If cell_range is None, reads the entire tab."""
    client = _get_client()
    range_str = f"{tab}!{cell_range}" if cell_range else tab
    result = (
        client.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=range_str)
        .execute()
    )
    return result.get("values", [])


def get_tab_headers(tab: str) -> list[str]:
    """Return the first row (headers) of a tab."""
    rows = read_range(tab, "1:1")
    return rows[0] if rows else []


def read_all_rows(tab: str) -> list[dict]:
    """Read an entire tab and return rows as dicts keyed by header name.

    Skips columns with empty header names.
    """
    raw = read_range(tab)
    if len(raw) < 2:
        return []
    headers = raw[0]
    rows = []
    for row in raw[1:]:
        # Pad short rows with empty strings
        padded = row + [""] * (len(headers) - len(row))
        record = {}
        for h, v in zip(headers, padded):
            if h:  # skip unnamed columns
                record[h] = v
        rows.append(record)
    return rows
