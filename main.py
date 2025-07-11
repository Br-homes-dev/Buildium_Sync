'''
Main script to synchronize outstanding lease balances from Buildium
into a google sheet using the lease ID as a matching key

This script:
1. Pulls outstanding balances for all active leases from the Buildium API.
2. Reads the current lease IDs and row positions from a google sheet.
3. Updates rows in the sheet if a lease already exists in the outstanding balance sheet
4. Appends new rows for any leases that don't exist in the sheet.
'''

from buildium_client import fetch_outstanding_balances, fetch_lease_details
from sheets_client import get_existing_lease_ids, update_sheet_row, append_sheet_row

def main():
    '''
    Entry point of the sync script. Coordinates Buildium API Google Sheets API calls.
    to ensure the sheet reflects the latest outstanding balances for all activate leases.
    '''

    # step 1: Fetch all outstanding leases balances from Buildium 
    lease_balances = fetch_outstanding_balances()

    # step 2: Build a mapping of Lease ID -> row number from the google sheet 
    lease_id_map = get_existing_lease_ids()

    #step 3: Loop through each lease with an outstanding balance
    for lease in lease_balances:
        lease_id = str(lease['LeaseId'])        # Convert LeaseID to string for matching
        balance = lease['TotalBalance']         # Extract outstanding balance

    if lease_id in lease_id_map:
        # if lease already exists in the sheet, update its balance in the appropriate row
        row_index = lease_id_map[lease_id]
        update_sheet_row(row_index, balance)
    else:
        # if it's a new lease, fetch additional details to populate a full row
        details = fetch_lease_details(lease_id)
        append_sheet_row(details, balance, lease_id)

if __name__ == "__main__":
    main()