from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.config import CREDENTIALS_PATH, SCOPES


def get_sheets_client():
    """Return an authorized Google Sheets API v4 service object."""
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_PATH), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)
