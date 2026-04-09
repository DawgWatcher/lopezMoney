"""get_transactions tool — reads Tiller Transactions tab."""

from datetime import date, datetime

from src.sheets_client import read_all_rows

# Tiller uses M/D/YYYY for dates in this sheet
_DATE_FORMATS = ["%m/%d/%Y", "%m/%d/%y"]


def _parse_tiller_date(raw: str) -> date | None:
    """Parse a Tiller date string into a date object."""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_iso_date(raw: str) -> date:
    """Parse a YYYY-MM-DD string, raising ValueError on bad input."""
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"Invalid date '{raw}'. Expected ISO format YYYY-MM-DD."
        )


def get_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    max_rows: int = 500,
) -> list[dict]:
    """Return transactions from the Tiller sheet.

    Dates are optional ISO YYYY-MM-DD strings. If both are omitted, defaults
    to the current calendar month (1st through today).  Returns most-recent
    first, capped at max_rows.
    """
    today = date.today()

    if start_date is not None:
        start = _parse_iso_date(start_date)
    else:
        start = today.replace(day=1)

    if end_date is not None:
        end = _parse_iso_date(end_date)
    else:
        end = today

    rows = read_all_rows("Transactions")

    filtered = []
    for row in rows:
        raw_date = row.get("Date", "")
        d = _parse_tiller_date(raw_date)
        if d is None:
            continue
        if start <= d <= end:
            row["_parsed_date"] = d
            filtered.append(row)

    # Most recent first
    filtered.sort(key=lambda r: r["_parsed_date"], reverse=True)

    # Remove internal key before returning
    for r in filtered:
        del r["_parsed_date"]

    return filtered[:max_rows]
