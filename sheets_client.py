'''
sheets_client.py

Handles interaction with the Google Sheets API, including:
- Authenticating using a service account
- Reading existing lease rows and mapping Lease IDs to row numbers
- Updating rows with new outstanding balances
- Appending new rows for new leases with full details
'''

import os
import json
from typing import Dict
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Constants for sheet structure
SHEET_ID = os.environ.get("SHEET_ID")
SHEET_NAME = os.environ.get("SHEET_NAME")  # Example: "Lease Balances"
CREDENTIALS_PATH = "secrets/creds.json"

# Column indexes (A=0, B=1, ..., AA=26)
LEASE_ID_COL = 26  # AA
BALANCE_COL = 4    # E
APPEND_COLUMNS = 27  # number of columns from A to AA (0–26)


def get_sheets_service():
    '''
    Initializes the Google Sheets API client using the service account credentials.

    Returns:
        A Sheets API service client.
    '''
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()


def get_existing_lease_ids() -> Dict[str, int]:
    '''
    Reads the Lease ID column (AA) from the Google Sheet and builds a mapping
    of Lease ID → row index (1-based for Google Sheets API).

    Returns:
        A dictionary mapping Lease ID strings to row numbers.
    '''
    sheets = get_sheets_service()
    range_ = f"{SHEET_NAME}!AA3:AA"  # Skip header row

    result = sheets.values().get(spreadsheetId=SHEET_ID, range=range_).execute()
    values = result.get("values", [])

    lease_map = {}

    for i, row in enumerate(values):
        if row:
            lease_id = row[0].strip()
            lease_map[lease_id] = i + 3  # Row numbers start at 3 (AA3 is row 3)

    return lease_map


def update_sheet_row(row_index: int, balance: float):
    '''
    Updates the outstanding balance in column E of a specific row.

    Args:
        row_index: The 1-based row index to update.
        balance: The new balance amount to set.
    '''
    sheets = get_sheets_service()
    range_ = f"{SHEET_NAME}!E{row_index}"  # Column E = Outstanding Balance

    body = {
        "values": [[balance]]
    }

    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=range_,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()


def append_sheet_row(details: Dict, balance: float, lease_id: str):
    '''
    Appends a new row to the Google Sheet with full lease details.

    Args:
        details: Dictionary with 'tenant_name', 'phone_number', 'address'.
        balance: Outstanding balance to insert into column E.
        lease_id: Unique lease ID to place into column AA.
    '''
    sheets = get_sheets_service()

    new_row = [
        details.get("tenant_name", ""),   # Column A
        details.get("address", ""),       # Column B
        details.get("phone_number", ""),  # Column C
        "",                               # Column D (unused)
        balance                           # Column E
    ]

    # Fill rest with blanks until column AA (index 26), then insert lease ID
    while len(new_row) < LEASE_ID_COL:
        new_row.append("")

    new_row.append(lease_id)  # Column AA

    body = {
        "values": [new_row]
    }

    range_ = f"{SHEET_NAME}!A:AA"

    sheets.values().append(
        spreadsheetId=SHEET_ID,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()
