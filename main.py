'''
Main script to synchronize outstanding lease balances from Buildium
into a Google Sheet using the Lease ID as a matching key.

This script:
1. Pulls outstanding balances for all active leases from the Buildium API.
2. Reads the current Lease IDs and row positions from a Google Sheet.
3. Updates rows in the sheet if a lease already exists.
4. Appends new rows for any leases that don’t exist in the sheet.
'''

from flask import Flask
from buildium_client import fetch_outstanding_balances, fetch_lease_details
from sheets_client import (
    get_existing_lease_ids,
    batch_update_balances,
    batch_append_new_leases
)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

@app.route("/", methods=["GET"])
def sync_lease_balances():
    '''
    Syncs outstanding lease balances from Buildium to Google Sheets.
    '''
    try:
        lease_balances = fetch_outstanding_balances()
        lease_id_map = get_existing_lease_ids()

        updates = []  # (row_idx, balance)
        new_leases = []  # (details_dict, balance, lease_id)

        for lease in lease_balances:
            lease_id = str(lease["LeaseId"])
            balance = lease["TotalBalance"]

            if lease_id in lease_id_map:
                updates.append((lease_id_map[lease_id], balance))
            else:
                details = fetch_lease_details(lease_id)
                new_leases.append((details, balance, lease_id))

        if updates:
            batch_update_balances(updates)

        if new_leases:
            batch_append_new_leases(new_leases)

        return f"✅ Synced {len(updates)} updates, added {len(new_leases)} new rows.", 200

    except Exception as e:
        return f"❌ Sync failed: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

