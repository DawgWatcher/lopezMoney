"""get_category_summary tool — groups Transactions by Category."""

from collections import defaultdict
from datetime import date

from src.tools.get_transactions import get_transactions


def _to_float(raw: str) -> float:
    """Convert a currency string like '$1,234.56' or '-$50' to float."""
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def get_category_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Group transactions by Category and sum amounts.

    For Mixed-scope rows, splits using BusinessAmount/PersonalAmount columns.
    Returns [{category, total, count, scope_breakdown: {business, personal, unscoped}}].
    """
    txns = get_transactions(start_date=start_date, end_date=end_date, max_rows=10_000)

    cats: dict[str, dict] = defaultdict(
        lambda: {
            "total": 0.0,
            "count": 0,
            "scope_breakdown": {"business": 0.0, "personal": 0.0, "unscoped": 0.0},
        }
    )

    for txn in txns:
        category = txn.get("Category", "") or "Uncategorized"
        amount = _to_float(txn.get("Amount", ""))
        scope = (txn.get("Scope", "") or "").strip().lower()

        entry = cats[category]
        entry["total"] += amount
        entry["count"] += 1

        if scope == "business":
            entry["scope_breakdown"]["business"] += amount
        elif scope == "personal":
            entry["scope_breakdown"]["personal"] += amount
        elif scope == "mixed":
            biz = _to_float(txn.get("BusinessAmount", ""))
            pers = _to_float(txn.get("PersonalAmount", ""))
            entry["scope_breakdown"]["business"] += biz
            entry["scope_breakdown"]["personal"] += pers
        else:
            # No scope assigned — full amount is unscoped
            entry["scope_breakdown"]["unscoped"] += amount

    results = []
    for category, data in sorted(cats.items()):
        results.append(
            {
                "category": category,
                "total": round(data["total"], 2),
                "count": data["count"],
                "scope_breakdown": {
                    k: round(v, 2) for k, v in data["scope_breakdown"].items()
                },
            }
        )
    return results
