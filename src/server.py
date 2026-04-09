from fastmcp import FastMCP

from src.tools.get_transactions import get_transactions
from src.tools.get_balances import get_balances
from src.tools.get_scheduled_payments import get_scheduled_payments
from src.tools.get_category_summary import get_category_summary
from src.tools.update_transaction_category import update_transaction_category
from src.tools.update_transaction_scope import update_transaction_scope
from src.tools.split_mixed_transaction import split_mixed_transaction

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


@mcp.tool()
def tool_update_transaction_category(
    transaction_id: str,
    category: str,
) -> dict:
    """Update the Category of a transaction.

    Args:
        transaction_id: The Transaction ID to update.
        category: The new category name. Must exist in the Tiller Categories tab.

    Validates the category, writes the cell, and verifies via optimistic locking.
    """
    return update_transaction_category(
        transaction_id=transaction_id, category=category
    )


@mcp.tool()
def tool_update_transaction_scope(
    transaction_id: str,
    scope: str,
    business_amount: float | None = None,
    personal_amount: float | None = None,
) -> dict:
    """Update the Scope of a transaction (Business, Personal, or Mixed).

    Args:
        transaction_id: The Transaction ID to update.
        scope: One of "Business", "Personal", or "Mixed".
        business_amount: Required for Mixed scope. The business portion.
        personal_amount: Required for Mixed scope. The personal portion.

    For Mixed scope, also writes BusinessAmount and PersonalAmount cells.
    For non-Mixed scopes, clears those cells.
    """
    return update_transaction_scope(
        transaction_id=transaction_id,
        scope=scope,
        business_amount=business_amount,
        personal_amount=personal_amount,
    )


@mcp.tool()
def tool_split_mixed_transaction(
    transaction_id: str,
    business_amount: float,
    personal_amount: float,
) -> dict:
    """Set a transaction to Mixed scope with a business/personal split.

    Args:
        transaction_id: The Transaction ID to update.
        business_amount: The business portion of the amount.
        personal_amount: The personal portion of the amount.

    Convenience wrapper around update_transaction_scope with scope="Mixed".
    """
    return split_mixed_transaction(
        transaction_id=transaction_id,
        business_amount=business_amount,
        personal_amount=personal_amount,
    )


if __name__ == "__main__":
    mcp.run()
