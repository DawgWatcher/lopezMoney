"""Smoke test: authenticate and print the Tiller sheet title + tab names."""

import sys
from pathlib import Path

# Allow running as `python tests/smoke_test.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth import get_sheets_client
from src.config import SHEET_ID


def main():
    try:
        sheets = get_sheets_client()
        spreadsheet = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    except Exception as exc:
        print(f"AUTH FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    title = spreadsheet["properties"]["title"]
    tabs = [s["properties"]["title"] for s in spreadsheet["sheets"]]

    print(f"Sheet title: {title}")
    print(f"Tabs ({len(tabs)}): {', '.join(tabs)}")


if __name__ == "__main__":
    main()
