"""split_mixed_transaction — Phase 3 convenience wrapper."""

from src.tools.update_transaction_scope import update_transaction_scope


def split_mixed_transaction(
    transaction_id: str,
    business_amount: float,
    personal_amount: float,
) -> dict:
    """Set a transaction to Mixed scope with the given split amounts.

    Thin convenience wrapper around update_transaction_scope.
    """
    return update_transaction_scope(
        transaction_id=transaction_id,
        scope="Mixed",
        business_amount=business_amount,
        personal_amount=personal_amount,
    )
