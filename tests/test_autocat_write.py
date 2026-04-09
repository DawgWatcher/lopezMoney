"""Live tests for Phase 3.5 append_autocat_rule against the real Tiller sheet.

All tests run against the live sheet — no mocks. Each test that writes
clears the row in a finally block to prevent test pollution.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import get_sheets_client
from src.concurrency import LOCK_PATH, LockAcquisitionError, LockFile
from src.config import SHEET_ID
from src.sheets_client import read_range
from src.tools.append_autocat_rule import append_autocat_rule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_autocat_row(row: int) -> None:
    """Write 6 empty strings to clear an AutoCat row."""
    client = get_sheets_client()
    client.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"AutoCat!A{row}:F{row}",
        valueInputOption="RAW",
        body={"values": [["", "", "", "", "", ""]]},
    ).execute()


def _first_empty_autocat_row() -> int:
    """Return the 1-indexed row number of the first empty AutoCat data row."""
    raw = read_range("AutoCat")
    for i, row in enumerate(raw[1:], start=2):
        padded = row + [""] * (6 - len(row))
        if all(cell == "" for cell in padded[:6]):
            return i
    return len(raw) + 1


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path():
    """1. Write a rule, verify return + sheet contents, clean up."""
    row_before = _first_empty_autocat_row()

    row = None
    try:
        result = append_autocat_rule(
            category="Restaurants",
            description_contains="test_merchant_xyz",
        )
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert result["row"] >= 3, f"Expected row >= 3, got {result['row']}"
        assert result["category"] == "Restaurants"
        assert result["description_contains"] == "test_merchant_xyz"
        row = result["row"]

        # Verify the write on the sheet
        verify = read_range("AutoCat", f"A{row}:F{row}")
        assert verify and verify[0], "Row should not be empty after write"
        assert verify[0][0] == "Restaurants"
        assert verify[0][1] == "test_merchant_xyz"
        print(f"  Wrote rule to row {row}, verified on sheet")
    finally:
        if row is not None:
            _clear_autocat_row(row)
            print(f"  Cleaned up row {row}")
    print("  PASS")


def test_unknown_category_rejection():
    """2. Attempt an invalid category; assert ValueError, no row written."""
    row_before = _first_empty_autocat_row()

    try:
        append_autocat_rule(
            category="ZZZNonExistent",
            description_contains="anything",
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown category" in str(e), f"Unexpected error: {e}"

    # Verify the first empty row hasn't moved
    row_after = _first_empty_autocat_row()
    assert row_after == row_before, (
        f"First empty row moved from {row_before} to {row_after} — "
        "a row was written despite invalid category"
    )
    print(f"  Correctly rejected 'ZZZNonExistent'; no row written")
    print("  PASS")


def test_lockfile_self_race():
    """3. Acquire lockfile, then attempt append — must raise LockAcquisitionError."""
    with LockFile():
        try:
            append_autocat_rule(
                category="Restaurants",
                description_contains="test_lock_race",
            )
            assert False, "Should have raised LockAcquisitionError"
        except LockAcquisitionError as e:
            assert "Another write is in progress" in str(e)
            print(f"  Self-race correctly rejected: {e}")
    assert not LOCK_PATH.exists(), "Lockfile should be gone after with-block exit"
    print("  PASS")


def test_post_write_verification():
    """4. Write a rule, independently re-read the row, verify match, clean up."""
    row = None
    try:
        result = append_autocat_rule(
            category="Restaurants",
            description_contains="test_verify_xyz",
        )
        assert result["status"] == "ok"
        row = result["row"]

        # Independent re-read (not relying on the tool's internal verification)
        verify = read_range("AutoCat", f"A{row}:F{row}")
        assert verify and verify[0], "Row should not be empty"
        assert verify[0][0] == "Restaurants", (
            f"Category mismatch: expected 'Restaurants', got '{verify[0][0]}'"
        )
        assert verify[0][1] == "test_verify_xyz", (
            f"Description mismatch: expected 'test_verify_xyz', got '{verify[0][1]}'"
        )
        # Optional columns should be empty strings
        padded = verify[0] + [""] * (6 - len(verify[0]))
        assert padded[2] == "", f"Account should be empty, got '{padded[2]}'"
        assert padded[3] == "", f"Institution should be empty, got '{padded[3]}'"
        assert padded[4] == "", f"Amount Min should be empty, got '{padded[4]}'"
        assert padded[5] == "", f"Amount Max should be empty, got '{padded[5]}'"
        print(f"  Post-write verification passed for row {row}")
    finally:
        if row is not None:
            _clear_autocat_row(row)
            print(f"  Cleaned up row {row}")
    print("  PASS")


def test_optional_parameters():
    """5. Write a rule with optional params; verify populated/empty columns; clean up."""
    row = None
    try:
        result = append_autocat_rule(
            category="Restaurants",
            description_contains="test_optional_xyz",
            account_contains="Chase",
            amount_min=10.00,
        )
        assert result["status"] == "ok"
        row = result["row"]

        verify = read_range("AutoCat", f"A{row}:F{row}")
        assert verify and verify[0], "Row should not be empty"
        padded = verify[0] + [""] * (6 - len(verify[0]))
        assert padded[0] == "Restaurants"
        assert padded[1] == "test_optional_xyz"
        assert padded[2] == "Chase", f"Account should be 'Chase', got '{padded[2]}'"
        assert padded[3] == "", f"Institution should be empty, got '{padded[3]}'"
        # Sheets may return "10" or "10.0" for a raw-written float
        assert padded[4] != "", f"Amount Min should be populated, got empty"
        assert float(padded[4]) == 10.0, (
            f"Amount Min should be 10.0, got {padded[4]}"
        )
        assert padded[5] == "", f"Amount Max should be empty, got '{padded[5]}'"
        print(f"  Optional params verified: account='Chase', amount_min=10.0")
    finally:
        if row is not None:
            _clear_autocat_row(row)
            print(f"  Cleaned up row {row}")
    print("  PASS")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    tests = [
        test_happy_path,
        test_unknown_category_rejection,
        test_lockfile_self_race,
        test_post_write_verification,
        test_optional_parameters,
    ]
    failed = 0
    for test in tests:
        print(f"\n{'=' * 60}")
        print(f"  {test.__name__}")
        print(f"{'=' * 60}")
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  {len(tests) - failed}/{len(tests)} tests passed")
    print(f"{'=' * 60}")
    sys.exit(1 if failed else 0)
