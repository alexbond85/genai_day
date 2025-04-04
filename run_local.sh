#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Set the service account to impersonate
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="chainlit-bq-reader@sandbox-shippeo-hackathon-cc0a.iam.gserviceaccount.com"

# Optional: Set a specific port for Chainlit if needed
# export CHAINLIT_PORT=8080

echo "--- Starting Chainlit locally with impersonation for SA: ${GOOGLE_IMPERSONATE_SERVICE_ACCOUNT} ---"

# Run Chainlit (add -w for auto-reload if desired)
chainlit run app.py -w

echo "--- Chainlit stopped ---" 