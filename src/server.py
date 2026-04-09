from fastmcp import FastMCP

from src.tools.get_transactions import get_transactions
from src.tools.get_balances import get_balances
from src.tools.get_scheduled_payments import get_scheduled_payments
from src.tools.get_category_summary import get_category_summary

mcp = FastMCP("finance-enforcer")


@mcp.tool()
def tool_get_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    max_rows: int = 500,
) -> list[dict]:
    """Fetch transactions from the Tiller sheet.

    Args:
        start_date: Optional start date in YYYY-MM-DD format.
        end_date: Optional end date in YYYY-MM-DD format.
        max_rows: Maximum number of rows to return (default 500).

    If both dates are omitted, defaults to the current calendar month.
    Returns most-recent-first, including Scope/BusinessAmount/PersonalAmount.
    """
    return get_transactions(start_date=start_date, end_date=end_date, max_rows=max_rows)


@mcp.tool()
def tool_get_balances() -> list[dict]:
    """Fetch current account balances from the Tiller sheet.

    Returns one dict per account with account name, institution, type,
    balance, and last-updated date.
    """
    return get_balances()


@mcp.tool()
def tool_get_scheduled_payments() -> list[dict]:
    """Fetch future-dated transactions (scheduled payments) from Tiller.

    Returns transactions whose date is after today, or an empty list if
    none exist.
    """
    return get_scheduled_payments()


@mcp.tool()
def tool_get_category_summary(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Summarize transactions grouped by category.

    Args:
        start_date: Optional start date in YYYY-MM-DD format.
        end_date: Optional end date in YYYY-MM-DD format.

    Returns category name, total amount, transaction count, and a
    scope breakdown (business/personal/mixed).
    """
    return get_category_summary(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    mcp.run()
