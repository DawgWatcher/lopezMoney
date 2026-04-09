"""Live tests for Phase 3 write tools against the real Tiller sheet.

All tests run against the live sheet — no mocks. Each test that writes
restores the original cell values in a finally block.
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.concurrency import LOCK_PATH, LockAcquisitionError, LockFile
from src.sheets_client import read_all_rows
from src.tools.get_transactions import get_transactions
from src.tools.split_mixed_transaction import split_mixed_transaction
from src.tools.update_transaction_category import (
    _find_transaction_row,
    _write_cells,
    update_transaction_category,
)
from src.tools.update_transaction_scope import update_transaction_scope

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _get_test_transaction() -> dict:
    """Return a recent transaction that has a Transaction ID."""
    txns = get_transactions(max_rows=20)
    for t in txns:
        if t.get("Transaction ID"):
            return t
    raise AssertionError("No transaction with a Transaction ID found")


def _get_two_valid_categories() -> tuple[str, str]:
    """Return two distinct valid category names from the Categories tab."""
    cats = read_all_rows("Categories")
    names = [r["Category"] for r in cats if r.get("Category")]
    if len(names) < 2:
        raise AssertionError("Need at least 2 categories for testing")
    return names[0], names[1]


def _restore_cells(transaction_id: str, updates: dict) -> None:
    """Direct-write restore without validation (handles empty strings)."""
    sheet_row, _, _, col_map = _find_transaction_row(transaction_id)
    _write_cells(sheet_row, col_map, updates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_category_update():
    """1. Set a known transaction's Category to a valid value, then reset."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    original_cat = txn.get("Category", "")
    cat_a, cat_b = _get_two_valid_categories()
    new_cat = cat_b if original_cat == cat_a else cat_a

    try:
        result = update_transaction_category(tid, new_cat)
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert result["new_category"] == new_cat
        assert result["old_category"] == original_cat
        assert not LOCK_PATH.exists(), "Lockfile should be gone"
        print(f"  Set {tid[:12]}... category → {new_cat}")
    finally:
        _restore_cells(tid, {"Category": original_cat})
        print(f"  Restored category → '{original_cat}'")
    print("  PASS")


def test_unknown_category_rejection():
    """2. Attempt an invalid category; assert ValueError, no cell written."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    original_cat = txn.get("Category", "")

    try:
        update_transaction_category(tid, "ZZZNonExistent")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown category" in str(e), f"Unexpected error: {e}"

    # Verify nothing was written
    sheet_row, row_data, _, _ = _find_transaction_row(tid)
    assert row_data.get("Category", "") == original_cat, (
        f"Category should be unchanged; got '{row_data.get('Category')}'"
    )
    assert not LOCK_PATH.exists(), "Lockfile should be gone after error"
    print(f"  Correctly rejected 'ZZZNonExistent'")
    print("  PASS")


def test_happy_scope_personal():
    """3. Set a known row to Personal; verify amounts are cleared; reset."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    orig = {
        "Scope": txn.get("Scope", ""),
        "BusinessAmount": txn.get("BusinessAmount", ""),
        "PersonalAmount": txn.get("PersonalAmount", ""),
    }

    try:
        result = update_transaction_scope(tid, "Personal")
        assert result["status"] == "ok"
        assert result["scope"] == "Personal"

        # Read back and verify amounts are empty
        _, row_data, _, _ = _find_transaction_row(tid)
        assert row_data.get("BusinessAmount", "") == "", (
            f"BusinessAmount should be empty, got '{row_data.get('BusinessAmount')}'"
        )
        assert row_data.get("PersonalAmount", "") == "", (
            f"PersonalAmount should be empty, got '{row_data.get('PersonalAmount')}'"
        )
        assert row_data.get("Scope") == "Personal"
        print(f"  Set {tid[:12]}... scope → Personal (amounts cleared)")
    finally:
        _restore_cells(tid, orig)
        print(f"  Restored scope → '{orig['Scope']}'")
    print("  PASS")


def test_happy_scope_mixed_with_split():
    """4. Set a known row to Mixed with split amounts; verify; reset."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    orig = {
        "Scope": txn.get("Scope", ""),
        "BusinessAmount": txn.get("BusinessAmount", ""),
        "PersonalAmount": txn.get("PersonalAmount", ""),
    }

    try:
        result = update_transaction_scope(
            tid, "Mixed", business_amount=10.00, personal_amount=15.00
        )
        assert result["status"] == "ok"
        assert result["scope"] == "Mixed"
        assert result["business_amount"] == 10.00
        assert result["personal_amount"] == 15.00

        # Read back and verify all three cells
        _, row_data, _, _ = _find_transaction_row(tid)
        assert row_data.get("Scope") == "Mixed"
        # Sheets may return "10" or "10.0" for a raw-written float
        ba = float(row_data.get("BusinessAmount", "0"))
        pa = float(row_data.get("PersonalAmount", "0"))
        assert ba == 10.0, f"BusinessAmount should be 10.0, got {ba}"
        assert pa == 15.0, f"PersonalAmount should be 15.0, got {pa}"
        print(f"  Set {tid[:12]}... scope → Mixed (10.00 / 15.00)")
    finally:
        _restore_cells(tid, orig)
        print(f"  Restored scope → '{orig['Scope']}'")
    print("  PASS")


def test_validation_mixed_without_both_amounts():
    """5. Attempt Mixed scope with only business_amount; assert ValueError."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    try:
        update_transaction_scope(tid, "Mixed", business_amount=10.00)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "both business_amount and personal_amount" in str(e), (
            f"Unexpected error: {e}"
        )
    assert not LOCK_PATH.exists(), "Lockfile should be gone after validation error"
    print("  Correctly rejected Mixed without personal_amount")
    print("  PASS")


def test_validation_non_mixed_with_amounts():
    """6. Attempt Personal scope with business_amount; assert ValueError."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    try:
        update_transaction_scope(tid, "Personal", business_amount=5.00)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Non-Mixed scope cannot have split amounts" in str(e), (
            f"Unexpected error: {e}"
        )
    assert not LOCK_PATH.exists(), "Lockfile should be gone after validation error"
    print("  Correctly rejected Personal with business_amount")
    print("  PASS")


def test_lockfile_self_race():
    """7. Acquire lockfile, then attempt a write from inside — must raise."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    cat_a, _ = _get_two_valid_categories()

    with LockFile():
        try:
            update_transaction_category(tid, cat_a)
            assert False, "Should have raised LockAcquisitionError"
        except LockAcquisitionError as e:
            assert "Another write is in progress" in str(e)
            print(f"  Self-race correctly rejected: {e}")
    assert not LOCK_PATH.exists(), "Lockfile should be gone after with-block exit"
    print("  PASS")


def test_lockfile_stale_release():
    """8. Write a lockfile 120s old, then perform a write; must succeed."""
    txn = _get_test_transaction()
    tid = txn["Transaction ID"]
    original_cat = txn.get("Category", "")
    cat_a, cat_b = _get_two_valid_categories()
    new_cat = cat_b if original_cat == cat_a else cat_a

    # Plant a stale lockfile
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    LOCK_PATH.write_text(
        json.dumps({"pid": 99999, "acquired_at": stale_time.isoformat()})
    )

    try:
        result = update_transaction_category(tid, new_cat)
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert not LOCK_PATH.exists(), "Lockfile should be gone"
        print(f"  Stale lock overridden; write succeeded → {new_cat}")
    finally:
        _restore_cells(tid, {"Category": original_cat})
        # Also clean up stale lock just in case
        LOCK_PATH.unlink(missing_ok=True)
        print(f"  Restored category → '{original_cat}'")
    print("  PASS")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    tests = [
        test_happy_category_update,
        test_unknown_category_rejection,
        test_happy_scope_personal,
        test_happy_scope_mixed_with_split,
        test_validation_mixed_without_both_amounts,
        test_validation_non_mixed_with_amounts,
        test_lockfile_self_race,
        test_lockfile_stale_release,
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
