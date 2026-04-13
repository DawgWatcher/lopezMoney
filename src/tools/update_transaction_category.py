"""update_transaction_category — Phase 3 write tool.

Also exports shared write helpers used by update_transaction_scope.
"""

from src.auth import get_sheets_client
from src.concurrency import (
    ConcurrentModificationError,
    LockFile,
    identity_tuple,
)
from src.config import SHEET_ID
from src.sheets_client import read_all_rows, read_range


# ---------------------------------------------------------------------------
# Shared write helpers (imported by update_transaction_scope)
# ---------------------------------------------------------------------------

def _col_letter(index: int) -> str:
    """Convert a 0-based column index to a spreadsheet column letter."""
    result = ""
    while True:
        result = chr(ord("A") + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


def _find_transaction_row(
    transaction_id: str,
) -> tuple[int, dict, list[str], dict[str, int]]:
    """Locate a row in the Transactions tab by Transaction ID.

    Returns (sheet_row_number, row_dict, headers_list, col_name_to_index).
    sheet_row_number is 1-indexed (header = row 1, first data row = row 2).
    Columns are looked up by header name, never by position.
    """
    raw = read_range("Transactions")
    if len(raw) < 2:
        raise ValueError("Transactions tab is empty")

    headers = raw[0]
    col_map = {h: i for i, h in enumerate(headers) if h}

    if "Transaction ID" not in col_map:
        raise KeyError("'Transaction ID' column not found in Transactions tab")

    tid_col = col_map["Transaction ID"]

    for data_idx, raw_row in enumerate(raw[1:]):
        sheet_row = data_idx + 2  # 1-indexed, header is row 1
        padded = raw_row + [""] * (len(headers) - len(raw_row))
        if padded[tid_col] == transaction_id:
            row_dict = {h: padded[i] for i, h in enumerate(headers) if h}
            return sheet_row, row_dict, headers, col_map

    raise ValueError(f"Transaction ID '{transaction_id}' not found")


def _write_cells(
    row_number: int,
    col_map: dict[str, int],
    updates: dict[str, str | float | int],
) -> None:
    """Write values to specific cells in the Transactions tab.

    Columns are resolved by header name via col_map.
    """
    client = get_sheets_client()
    for col_name, value in updates.items():
        if col_name not in col_map:
            raise KeyError(
                f"Column '{col_name}' not found in Transactions tab"
            )
        col_letter = _col_letter(col_map[col_name])
        cell_range = f"Transactions!{col_letter}{row_number}"
        client.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [[value]]},
        ).execute()


def _re_read_row(row_number: int, headers: list[str]) -> dict:
    """Re-read a specific row from the Transactions tab for optimistic-lock check."""
    last_col = _col_letter(len(headers) - 1)
    range_str = f"A{row_number}:{last_col}{row_number}"
    raw = read_range("Transactions", range_str)
    if not raw:
        raise ValueError(f"Row {row_number} not found on re-read")
    raw_row = raw[0]
    padded = raw_row + [""] * (len(headers) - len(raw_row))
    return {h: padded[i] for i, h in enumerate(headers) if h}


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

def update_transaction_category(transaction_id: str, category: str) -> dict:
    """Update the Category of a transaction in the Tiller Transactions tab.

    Validates that the category exists in the Categories tab.
    Uses lockfile + optimistic locking for concurrency safety.
    """
    with LockFile():
        # Validate category against the Categories tab
        cat_rows = read_all_rows("Categories")
        valid_categories = {
            row["Category"] for row in cat_rows if row.get("Category")
        }
        if category not in valid_categories:
            raise ValueError(
                f"Unknown category: {category}. "
                "Create it manually in the Tiller Categories tab before retrying."
            )

        # Locate the target row
        sheet_row, row_data, headers, col_map = _find_transaction_row(
            transaction_id
        )

        # Pre-write snapshot for optimistic locking
        pre_write = identity_tuple(row_data)
        old_category = row_data.get("Category", "")

        # Write the new category
        _write_cells(sheet_row, col_map, {"Category": category})

        # Post-write verification
        post_row = _re_read_row(sheet_row, headers)
        post_write = identity_tuple(post_row)
        if pre_write != post_write:
            raise ConcurrentModificationError(
                "Row was modified during write — re-read and retry"
            )

    return {
        "transaction_id": transaction_id,
        "old_category": old_category,
        "new_category": category,
        "status": "ok",
    }
