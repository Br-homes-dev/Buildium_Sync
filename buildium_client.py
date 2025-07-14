'''
buildium_client.py

Handles interaction with the buildium API, including:
- Authenticating using client ID and secret
- Fetching outstanding lease balances
- Fetching details about a specific lease
'''

import os
import requests
from typing import List, Dict

# Load credentials from env
BUILD_IUM_CLIENT_ID = os.environ.get("BUILD_IUM_CLIENT_ID")
BUILD_IUM_CLIENT_SECRET = os.environ.get("BUILD_IUM_CLIENT_SECRET")

# Base URL for Buildium API
BUILDIUM_API_BASE = "https://api.buildium.com/v1"

# Global var to cache auth token after it's been fetched
_auth_token = None

def get_auth_headers() -> Dict[str, str]:
    '''
    Fetched and returns the auth headers required for Buildium API calls

    Returns:
    A dictionary containing the 'Authorization' and 'Content-Type' headers.
    '''

    global _auth_token

    if _auth_token is None:
        # Step 1: Request a new token using the client creds
        response = requests.post(
            "https://api.buildium.com/v1/token",
            data={
                "grant_type": "client_credentials",
                "client_id": BUILD_IUM_CLIENT_ID,
                "client_secret": BUILD_IUM_CLIENT_SECRET
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        if response.status_code != 200:
            raise Exception(f"Failed to authenticate with Buildium: {response.text}")
        
        _auth_token = response.json()["access_token"]

    # Step 2: Return the header for reuse
    return {
        "Authorization": f"Bearer {_auth_token}",
        "Content-Type": "application/json"
    }

def fetch_outstanding_balances() -> List[Dict]:
    '''
    Fetches a list of leases that have outstanding balances from the Buildium API.

    Returns:
    A list of dictionaries each representing a lease with an outstanding balance.
    '''

    url = f"{BUILDIUM_API_BASE}/leases/outstandingbalances"

    response = requests.get(url, headers=get_auth_headers())

    if response.status_code != 200:
        raise Exception(f"Failed to fetch outstanding balances: {response.text}")
    
    return response.json()

def fetch_lease_details(lease_id: str) -> Dict:
    '''
    Fetches detailed lease information for a given lease ID, including tenant information
    and property address (used when appending a new row).

    Args:
        lease_id: The lease ID to look up
    
    Returns:
        A dictionary with tenant name, phone number and property address.
    '''

    # step 1: Fetch lease details (to get tenant and property IDs)
    lease_url = f"{BUILDIUM_API_BASE}/leases/{lease_id}"
    lease_res = requests.get(lease_url, headers=get_auth_headers())

    if lease_res.status_code != 200:
        raise Exception(f"Failed to fetch lease details: {lease_res.text}")
    
    lease_data = lease_res.json()

    # Extract relevant IDs
    tenant = lease_data.get("CurrentTenants", [{}])[0]
    property_id = lease_data.get("PropertyId")

    # step 2: Fetch property info
    property_url = f"{BUILDIUM_API_BASE}/rentals/{property_id}"
    prop_res = requests.get(property_url, headers=get_auth_headers())

    if prop_res.status_code != 200:
        raise Exception(f"Failed to fetch property details: {prop_res.text}")
    
    property_data = prop_res.json()

    # Step 3: Normalize and return final payload
    return {
        "tenant_name": f"{tenant.get('FirstName', '')} {tenant.get('LastName', '')}".strip(),
        "phone_number": tenant.get("PhoneNumbers", [{}])[0].get("Number", ""),
        "address": property_data.get("Address", {}).get("AddressLine1", "")
    }