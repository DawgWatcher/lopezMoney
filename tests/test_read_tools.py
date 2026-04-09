"""Live tests for Phase 2 read tools against the real Tiller sheet."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.get_transactions import get_transactions
from src.tools.get_balances import get_balances
from src.tools.get_scheduled_payments import get_scheduled_payments
from src.tools.get_category_summary import get_category_summary


def _pp(label: str, data, sample: int = 3):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  Total results: {len(data)}")
    for item in data[:sample]:
        print(f"  {json.dumps(item, indent=2, default=str)}")
    if len(data) > sample:
        print(f"  ... and {len(data) - sample} more")


def test_get_transactions():
    txns = get_transactions()
    assert len(txns) > 0, "Expected non-empty transactions for current month"
    # Verify dict shape
    first = txns[0]
    assert "Date" in first, f"Missing 'Date' key. Keys: {list(first.keys())}"
    assert "Amount" in first, f"Missing 'Amount' key."
    assert "Description" in first, f"Missing 'Description' key."
    _pp("get_transactions (current month)", txns)
    print("  PASS")


def test_get_transactions_date_filter():
    txns = get_transactions(start_date="2026-03-01", end_date="2026-03-31")
    assert len(txns) > 0, "Expected transactions in March 2026"
    _pp("get_transactions (March 2026)", txns)
    print("  PASS")


def test_get_transactions_bad_date():
    try:
        get_transactions(start_date="not-a-date")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"\n  get_transactions bad date error (expected): {e}")
        print("  PASS")


def test_get_balances():
    bals = get_balances()
    assert len(bals) > 0, "Expected non-empty balances"
    first = bals[0]
    assert "account" in first, f"Missing 'account' key. Keys: {list(first.keys())}"
    assert "balance" in first, f"Missing 'balance' key."
    _pp("get_balances", bals)
    print("  PASS")


def test_get_scheduled_payments():
    payments = get_scheduled_payments()
    # May legitimately be empty
    _pp("get_scheduled_payments", payments)
    print(f"  Result count: {len(payments)} (empty list is OK)")
    print("  PASS")


def test_get_category_summary():
    summary = get_category_summary()
    assert len(summary) > 0, "Expected non-empty category summary"
    first = summary[0]
    assert "category" in first
    assert "total" in first
    assert "count" in first
    assert "scope_breakdown" in first
    sb = first["scope_breakdown"]
    assert set(sb.keys()) == {"business", "personal", "unscoped"}, (
        f"Expected keys {{business, personal, unscoped}}, got {set(sb.keys())}"
    )
    # Current month: no Scope values assigned yet → all unscoped
    assert sb["unscoped"] != 0, "Expected unscoped != 0 for current month"
    assert sb["business"] == 0, f"Expected business == 0, got {sb['business']}"
    assert sb["personal"] == 0, f"Expected personal == 0, got {sb['personal']}"
    _pp("get_category_summary (current month)", summary, sample=5)
    print("  PASS")


def test_category_summary_scope_bucketing():
    """Synthetic test: verify each Scope value buckets correctly."""
    from unittest.mock import patch

    fake_rows = [
        {"Category": "Office", "Amount": "-$100.00", "Scope": "Business",
         "BusinessAmount": "", "PersonalAmount": ""},
        {"Category": "Office", "Amount": "-$50.00", "Scope": "Personal",
         "BusinessAmount": "", "PersonalAmount": ""},
        {"Category": "Office", "Amount": "-$200.00", "Scope": "Mixed",
         "BusinessAmount": "-$120.00", "PersonalAmount": "-$80.00"},
        {"Category": "Office", "Amount": "-$75.00", "Scope": "",
         "BusinessAmount": "", "PersonalAmount": ""},
        {"Category": "Food", "Amount": "-$30.00", "Scope": "Personal",
         "BusinessAmount": "", "PersonalAmount": ""},
    ]

    with patch("src.tools.get_category_summary.get_transactions", return_value=fake_rows):
        result = get_category_summary()

    by_cat = {r["category"]: r for r in result}

    # Office: biz=-100 + -120(mixed split) = -220, pers=-50 + -80(mixed split) = -130, unscoped=-75
    office = by_cat["Office"]
    assert office["total"] == -425.0, f"Office total: {office['total']}"
    assert office["count"] == 4
    assert office["scope_breakdown"]["business"] == -220.0, (
        f"Office business: {office['scope_breakdown']['business']}"
    )
    assert office["scope_breakdown"]["personal"] == -130.0, (
        f"Office personal: {office['scope_breakdown']['personal']}"
    )
    assert office["scope_breakdown"]["unscoped"] == -75.0, (
        f"Office unscoped: {office['scope_breakdown']['unscoped']}"
    )

    # Food: personal=-30, rest=0
    food = by_cat["Food"]
    assert food["total"] == -30.0
    assert food["scope_breakdown"]["personal"] == -30.0
    assert food["scope_breakdown"]["business"] == 0.0
    assert food["scope_breakdown"]["unscoped"] == 0.0

    # No "mixed" key anywhere
    for entry in result:
        assert "mixed" not in entry["scope_breakdown"], (
            f"Found 'mixed' key in {entry['category']}"
        )

    print("\n  test_category_summary_scope_bucketing: all assertions passed")
    print("  PASS")


if __name__ == "__main__":
    tests = [
        test_get_transactions,
        test_get_transactions_date_filter,
        test_get_transactions_bad_date,
        test_get_balances,
        test_get_scheduled_payments,
        test_get_category_summary,
        test_category_summary_scope_bucketing,
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n  FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  {len(tests) - failed}/{len(tests)} tests passed")
    print(f"{'=' * 60}")
    sys.exit(1 if failed else 0)
