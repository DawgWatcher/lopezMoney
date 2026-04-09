from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"

SHEET_ID = "16kYi0F-p6FWE9zwyM_WRaA8KKO4J9ZB8WSqGtJO86-Y"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
