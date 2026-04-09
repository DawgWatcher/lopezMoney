"""append_autocat_rule — Phase 3.5 write tool.

Appends a new categorization rule to the Tiller AutoCat tab.
"""

from src.auth import get_sheets_client
from src.concurrency import LockFile
from src.config import SHEET_ID
from src.sheets_client import read_all_rows, read_range


def append_autocat_rule(
    category: str,
    description_contains: str,
    account_contains: str | None = None,
    institution_contains: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
) -> dict:
    """Append a new rule to the Tiller AutoCat tab.

    Validates the category against the Categories tab, acquires the
    lockfile, finds the first empty row in AutoCat, writes the rule,
    and verifies the write committed.
    """
    # 1. Validate category against the Categories tab
    cat_rows = read_all_rows("Categories")
    valid_categories = {
        row["Category"] for row in cat_rows if row.get("Category")
    }
    if category not in valid_categories:
        raise ValueError(
            f"Unknown category: {category}. "
            "Create it manually in the Tiller Categories tab before retrying."
        )

    # 2. Acquire lockfile
    with LockFile():
        # 3. Read AutoCat to find the first empty row
        raw = read_range("AutoCat")
        # Row 1 is headers; data starts at row 2
        # Find first empty row: a row is empty if all 6 cells are empty
        target_row = len(raw) + 1  # default: one past the last returned row
        for i, row in enumerate(raw[1:], start=2):  # skip header row
            padded = row + [""] * (6 - len(row))
            if all(cell == "" for cell in padded[:6]):
                target_row = i
                break

        # 4. Write the new rule via Sheets v4 API
        values = [
            category,
            description_contains,
            account_contains or "",
            institution_contains or "",
            amount_min if amount_min is not None else "",
            amount_max if amount_max is not None else "",
        ]

        client = get_sheets_client()
        range_str = f"AutoCat!A{target_row}:F{target_row}"
        client.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=range_str,
            valueInputOption="RAW",
            body={"values": [values]},
        ).execute()

        # 5. Re-read the row to verify the write committed
        verify = read_range("AutoCat", f"A{target_row}:F{target_row}")
        if (
            not verify
            or not verify[0]
            or verify[0][0] != category
            or (len(verify[0]) < 2 or verify[0][1] != description_contains)
        ):
            raise RuntimeError(
                f"Post-write verification failed for AutoCat row {target_row}"
            )

    # 6. Lockfile released by context manager

    # 7. Return result
    return {
        "category": category,
        "description_contains": description_contains,
        "row": target_row,
        "status": "ok",
    }
