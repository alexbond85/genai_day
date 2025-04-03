#!/bin/bash

# Configuration
PROJECT_ID="sandbox-shippeo-hackathon-cc0a"
REGION="europe-west1"
SERVICE_NAME="chainlit-demo"
IMAGE_NAME="europe-west1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"

# Build the image for AMD64 architecture
echo "🏗️ Building Docker image for AMD64..."
docker build --platform linux/amd64 -t ${IMAGE_NAME} .

# Push the image to Artifact Registry
echo "⬆️ Pushing image to Artifact Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --project ${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')
echo "✅ Deployment complete!"
echo "🌎 Service URL: ${SERVICE_URL}" 