"""update_transaction_scope — Phase 3 write tool."""

from src.concurrency import (
    ConcurrentModificationError,
    LockFile,
    identity_tuple,
)
from src.tools.update_transaction_category import (
    _find_transaction_row,
    _re_read_row,
    _write_cells,
)

_VALID_SCOPES = {"Business", "Personal", "Mixed"}


def update_transaction_scope(
    transaction_id: str,
    scope: str,
    business_amount: float | None = None,
    personal_amount: float | None = None,
) -> dict:
    """Update the Scope (and optionally split amounts) of a transaction.

    For Mixed scope, both business_amount and personal_amount are required.
    For non-Mixed scopes, neither may be provided.
    Uses lockfile + optimistic locking for concurrency safety.
    """
    # Validate inputs before acquiring lock
    if scope not in _VALID_SCOPES:
        raise ValueError(
            f"Invalid scope '{scope}'. "
            f"Must be one of: {', '.join(sorted(_VALID_SCOPES))}"
        )

    if scope == "Mixed":
        if business_amount is None or personal_amount is None:
            raise ValueError(
                "Mixed scope requires both business_amount and personal_amount"
            )
    else:
        if business_amount is not None or personal_amount is not None:
            raise ValueError("Non-Mixed scope cannot have split amounts")

    with LockFile():
        # Locate the target row
        sheet_row, row_data, headers, col_map = _find_transaction_row(
            transaction_id
        )

        # Pre-write snapshot for optimistic locking
        pre_write = identity_tuple(row_data)

        # Build cell updates
        updates: dict[str, str | float] = {"Scope": scope}
        if scope == "Mixed":
            updates["BusinessAmount"] = business_amount
            updates["PersonalAmount"] = personal_amount
        else:
            # Clear split amounts for non-Mixed scopes
            updates["BusinessAmount"] = ""
            updates["PersonalAmount"] = ""

        # Write
        _write_cells(sheet_row, col_map, updates)

        # Post-write verification
        post_row = _re_read_row(sheet_row, headers)
        post_write = identity_tuple(post_row)
        if pre_write != post_write:
            raise ConcurrentModificationError(
                "Row was modified during write — re-read and retry"
            )

    return {
        "transaction_id": transaction_id,
        "scope": scope,
        "business_amount": business_amount,
        "personal_amount": personal_amount,
        "status": "ok",
    }
