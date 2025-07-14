import os
import requests
from flask import Flask, Response, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys

# Environment Variables
SHEET_ID = os.environ["SHEET_ID"]
SHEET_NAME = os.environ["SHEET_NAME"]
BUILD_IUM_CLIENT_ID = os.environ["BUILD_IUM_CLIENT_ID"]
BUILD_IUM_CLIENT_SECRET = os.environ["BUILD_IUM_CLIENT_SECRET"]

# Setup credentials and API client
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    "/secrets/creds.json", scopes=SCOPES
)
sheets = build("sheets", "v4", credentials=creds).spreadsheets()

app = Flask(__name__)
@app.before_request
def log_request():
    print(f"recived request: {request.path}", file=sys.stderr)

def get_lease_id_map():
    result = sheets.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!AA2:AA"
    ).execute()
    values = result.get("values", [])
    return {row[0]: idx + 2 for idx, row in enumerate(values) if row}

def get_outstanding_balances():
    all_balances = []
    limit = 1000
    offset = 0
    total_count = float("inf")

    while offset < total_count:
        url = f"https://api.buildium.com/v1/leases/outstandingbalances?limit={limit}&offset={offset}"
        res = requests.get(url, headers={
            "x-buildium-client-id": BUILD_IUM_CLIENT_ID,
            "x-buildium-client-secret": BUILD_IUM_CLIENT_SECRET,
            "Accept": "application/json",
        })
        if not res.ok:
            raise Exception(f"Buildium error: {res.status_code} - {res.text}")
        data = res.json()
        all_balances.extend(data)
        if len(data) < limit:
            break
        offset += limit
    return all_balances

def get_lease_details(lease_id):
    res = requests.get(f"https://api.buildium.com/v1/leases/{lease_id}", headers={
        "x-buildium-client-id": BUILD_IUM_CLIENT_ID,
        "x-buildium-client-secret": BUILD_IUM_CLIENT_SECRET,
        "Accept": "application/json",
    })
    return res.json() if res.ok else None

def get_property_details(property_id):
    res = requests.get(f"https://api.buildium.com/v1/rentals/{property_id}", headers={
        "x-buildium-client-id": BUILD_IUM_CLIENT_ID,
        "x-buildium-client-secret": BUILD_IUM_CLIENT_SECRET,
        "Accept": "application/json",
    })
    return res.json() if res.ok else None

def write_to_sheet(updates):
    data = [{
        "range": f"{SHEET_NAME}!E{row}",
        "values": [[value]]
    } for row, value in updates]
    sheets.values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": data}
    ).execute()

def append_new_rows(rows):
    if not rows:
        return
    sheets.values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A2:AA",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows}
    ).execute()

def sync_outstanding_balances():
    lease_map = get_lease_id_map()
    balances = get_outstanding_balances()

    updates = []
    new_rows = []

    for entry in balances:
        lease_id = str(entry["LeaseId"])
        balance = entry["TotalBalance"]
        matched_row = lease_map.get(lease_id)

        if matched_row:
            existing = sheets.values().get(
                spreadsheetId=SHEET_ID,
                range=f"{SHEET_NAME}!E{matched_row}"
            ).execute()
            current_value = float(existing.get("values", [["0"]])[0][0])
            if current_value != balance:
                updates.append((matched_row, balance))
            continue

        lease = get_lease_details(entry["LeaseId"])
        if not lease:
            continue

        # ✅ Safe handling of missing or empty CurrentTenants
        tenants = lease.get("CurrentTenants", [])
        if tenants:
            tenant = tenants[0]
            tenant_name = f"{tenant.get('FirstName', '')} {tenant.get('LastName', '')}".strip()
            phone = tenant.get("PhoneNumbers", [{}])[0].get("Number", "")
        else:
            tenant_name = ""
            phone = ""

        # Get address
        property_id = lease.get("PropertyId")
        address = ""
        if property_id:
            prop = get_property_details(property_id)
            if prop:
                address = prop.get("Address", {}).get("AddressLine1", "")

        # Construct row
        row = [""] * 27
        row[0] = tenant_name
        row[1] = address
        row[2] = phone
        row[4] = balance
        row[26] = lease_id

        new_rows.append(row)

    if updates:
        write_to_sheet(updates)
        print(f"✅ Updated {len(updates)} rows.")
    if new_rows:
        append_new_rows(new_rows)
        print(f"➕ Appended {len(new_rows)} new rows.")

    return f"✅ Synced {len(updates)} updates, {len(new_rows)} new rows."


@app.route("/")
def run_sync():
    try:
        result = sync_outstanding_balances()
        return result, 200
    except Exception as e:
        import traceback
        print(" Error:", traceback.format_exc(), file=sys.stderr)
        return f"❌ Sync failed: {e}", 500

@app.route("/health")
def health():
    return "👍 Healthy", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
