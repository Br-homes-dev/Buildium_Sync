import os
import requests
from typing import List, Dict

# Load credentials from env
BUILD_IUM_CLIENT_ID = os.environ.get("BUILD_IUM_CLIENT_ID")
BUILD_IUM_CLIENT_SECRET = os.environ.get("BUILD_IUM_CLIENT_SECRET")

BUILDIUM_API_BASE = "https://api.buildium.com/v1"

def get_auth_headers() -> Dict[str, str]:
    '''
    Returns the API key-style auth headers required by Buildium.
    '''
    return {
        "x-buildium-client-id": BUILD_IUM_CLIENT_ID.strip(),
        "x-buildium-client-secret": BUILD_IUM_CLIENT_SECRET.strip(),
        "Accept": "application/json"
    }

def fetch_outstanding_balances() -> List[Dict]:
    '''
    Fetches all outstanding balances using offset/limit paging.
    '''
    all_balances = []
    limit = 1000
    offset = 0
    total_count = float('inf')

    while offset < total_count:
        url = f"{BUILDIUM_API_BASE}/leases/outstandingbalances?limit={limit}&offset={offset}"
        response = requests.get(url, headers=get_auth_headers())

        if response.status_code != 200:
            raise Exception(f"Failed to fetch outstanding balances: {response.text}")

        data = response.json()
        all_balances.extend(data.get("Items", []))
        total_count = data.get("TotalCount", len(all_balances))
        offset += limit

    return all_balances

def fetch_lease_details(lease_id: str) -> Dict:
    '''
    Fetches lease + property info using separate Buildium API calls.
    '''
    lease_url = f"{BUILDIUM_API_BASE}/leases/{lease_id}"
    lease_res = requests.get(lease_url, headers=get_auth_headers())

    if lease_res.status_code != 200:
        raise Exception(f"Failed to fetch lease details: {lease_res.text}")

    lease_data = lease_res.json()
    tenant = lease_data.get("CurrentTenants", [{}])[0]
    property_id = lease_data.get("PropertyId")

    property_url = f"{BUILDIUM_API_BASE}/rentals/{property_id}"
    prop_res = requests.get(property_url, headers=get_auth_headers())

    if prop_res.status_code != 200:
        raise Exception(f"Failed to fetch property details: {prop_res.text}")

    property_data = prop_res.json()

    return {
        "tenant_name": f"{tenant.get('FirstName', '')} {tenant.get('LastName', '')}".strip(),
        "phone_number": tenant.get("PhoneNumbers", [{}])[0].get("Number", ""),
        "address": property_data.get("Address", {}).get("AddressLine1", "")
    }
