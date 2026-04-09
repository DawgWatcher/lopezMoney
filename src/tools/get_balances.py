"""get_balances tool — reads the Tiller Accounts tab."""

from src.sheets_client import read_all_rows


def get_balances() -> list[dict]:
    """Return one dict per account from the Accounts tab.

    Each dict contains: Account, Institution, Type, Balance, Last Update.
    """
    rows = read_all_rows("Accounts")
    results = []
    for row in rows:
        account = row.get("Account", "").strip()
        if not account:
            continue
        results.append(
            {
                "account": account,
                "account_number": row.get("Account #", ""),
                "institution": row.get("Institution", ""),
                "type": row.get("Type", ""),
                "class": row.get("Class", ""),
                "balance": row.get("Last Balance", ""),
                "last_updated": row.get("Last Update", ""),
            }
        )
    return results
