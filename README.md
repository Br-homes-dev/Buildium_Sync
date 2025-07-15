Buildium Google Sheets Sync Service
===================================

This project syncs outstanding lease balances from the Buildium API to a Google Sheet.
It is deployed as a Flask web service via Google Cloud Run and uses a service account
to authenticate with the Google Sheets API.

Features
--------
- Updates existing rows in the sheet based on Lease ID
- Appends new rows if Lease ID is not already present
- Safely logs requests and errors
- Includes /health endpoint for monitoring
- Environment variables and service account secrets handled securely
- Deployed with Cloud Run using IAM (no unauthenticated access)
- Supports scheduled execution via Cloud Scheduler

Requirements
------------
- Python 3.11+
- Google Cloud SDK installed and authenticated
- Docker

Environment Variables
---------------------
These must be passed to the container at runtime:

- SHEET_ID: ID of the target Google Sheet
- SHEET_NAME: Name of the sheet tab (e.g., "Trigger Test")
- BUILD_IUM_CLIENT_ID: Buildium API client ID
- BUILD_IUM_CLIENT_SECRET: Buildium API client secret

Deployment Steps
----------------
1. Build the Docker image:
   docker build -t gcr.io/lease-renew-revist/buildium-sync:vXX .

2. Push to Google Container Registry:
   docker push gcr.io/lease-renew-revist/buildium-sync:vXX

3. Deploy to Cloud Run (secure):
   gcloud run deploy buildium-sync ^
     --image gcr.io/lease-renew-revist/buildium-sync:vXX ^
     --platform managed ^
     --region us-central1 ^
     --no-allow-unauthenticated ^
     --set-env-vars "SHEET_ID=...,SHEET_NAME=...,BUILD_IUM_CLIENT_ID=...,BUILD_IUM_CLIENT_SECRET=..." ^
     --update-secrets "/secrets/creds.json=sheets-creds:latest"

4. Grant Cloud Run Invoker to Cloud Scheduler:
   gcloud run services add-iam-policy-binding buildium-sync ^
     --platform managed ^
     --region us-central1 ^
     --member="serviceAccount:429867287026-compute@developer.gserviceaccount.com" ^
     --role="roles/run.invoker"

5. Update Scheduler Job to use OIDC:
   gcloud scheduler jobs update http buildium-sync-job ^
     --location=us-central1 ^
     --uri="https://buildium-sync-429867287026.us-central1.run.app/" ^
     --http-method=GET ^
     --oidc-service-account-email="429867287026-compute@developer.gserviceaccount.com"

Endpoints
---------
- /          → Triggers a sync from Buildium to Google Sheets
- /health    → Returns a 200 OK if the service is up

Sphinx Docs
-----------
Run from /docs:

   make html

Open `docs/build/html/index.html` in your browser to view the documentation.

Notes
-----
- The project uses `googleapiclient` for Sheets API access
- Logs to stderr for visibility in Cloud Run
- Assumes your Google Sheet uses:
    - Column AA for Lease IDs
    - Column E for Outstanding Balances
