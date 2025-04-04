#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# !!! Replace the REPO_NAME placeholder with your actual value !!!
PROJECT_ID="sandbox-shippeo-hackathon-cc0a" # Inferred Google Cloud Project ID
REGION="europe-west1"                   # Google Cloud region (europe-west1 is Belgium)
SERVICE_NAME="chainlit-demo"             # Inferred Cloud Run service name
REPO_NAME="cloud-run-source-deploy"     # Verified Artifact Registry repository name
IMAGE_NAME="chainlit-app"               # Name for your Docker image
# ---

# Construct the full image path for Artifact Registry
ARTIFACT_REGISTRY_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest"

# --- Steps ---

echo "--- Configuring gcloud Docker credential helper ---"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --project=${PROJECT_ID}

echo "--- Building the Docker image ---"
# Build for AMD64 architecture, common for Cloud Run
docker build --platform linux/amd64 -t ${IMAGE_NAME} .

echo "--- Tagging the image for Artifact Registry ---"
docker tag ${IMAGE_NAME} ${ARTIFACT_REGISTRY_URL}

echo "--- Pushing the image to Artifact Registry ---"
# Ensure the Artifact Registry repository exists.
# You might need to create it first using:
# gcloud artifacts repositories create ${REPO_NAME} --repository-format=docker --location=${REGION} --description="Docker repository for Chainlit app" --project=${PROJECT_ID}
docker push ${ARTIFACT_REGISTRY_URL}

echo "--- Deploying to Cloud Run ---"
gcloud run deploy ${SERVICE_NAME} \
  --image ${ARTIFACT_REGISTRY_URL} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port=8000 \
  --service-account=chainlit-bq-reader@sandbox-shippeo-hackathon-cc0a.iam.gserviceaccount.com \
  --project ${PROJECT_ID}

echo "--- Deployment complete! ---"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}" 