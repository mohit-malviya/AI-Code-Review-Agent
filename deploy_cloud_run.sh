#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run Deployment Script for AI Code Review Agent
# ==============================================================================
set -euo pipefail

# Configurations - Update these variables according to your GCP project
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
SERVICE_NAME="${SERVICE_NAME:-ai-code-review-agent}"
REGION="${GCP_REGION:-us-central1}"
STORAGE_BACKEND="${STORAGE_BACKEND:-firestore}"

# Validate Project ID
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "your-gcp-project-id" ]]; then
  echo "==================================================================" >&2
  echo " ERROR: GCP PROJECT_ID is not configured!" >&2
  echo "==================================================================" >&2
  echo " The GCP_PROJECT_ID is currently empty or set to the placeholder:" >&2
  echo "   'your-gcp-project-id'" >&2
  echo "" >&2
  echo " Please set your Google Cloud Project ID by either:" >&2
  echo "   1. export GCP_PROJECT_ID='your-actual-project-id'" >&2
  echo "   2. Pass PROJECT_ID directly when invoking this script." >&2
  echo "==================================================================" >&2
  exit 1
fi

echo "=================================================================="
echo " Deploying AI Code Review Agent to Google Cloud Run"
echo " Project:  ${PROJECT_ID}"
echo " Service:  ${SERVICE_NAME}"
echo " Region:   ${REGION}"
echo "=================================================================="

# Set active GCP project
gcloud config set project "${PROJECT_ID}"

# Deploy from current source directory
# IMPORTANT flags:
#  --no-cpu-throttling: Ensures background tasks (AI review & email sending)
#                       continue processing after the HTTP 202 response.
#  --port 8080: Default Cloud Run port.
#  --allow-unauthenticated: Allows GitHub Webhook deliveries to reach the service.
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "STORAGE_BACKEND=${STORAGE_BACKEND}"

# Retrieve the assigned Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')

echo "=================================================================="
echo " Deployment Complete!"
echo " Service URL: ${SERVICE_URL}"
echo ""
echo " Required Next Steps:"
echo " 1. Update APPROVAL_BASE_URL to point to your deployed service:"
echo "    gcloud run services update ${SERVICE_NAME} --region ${REGION} --update-env-vars APPROVAL_BASE_URL=${SERVICE_URL}/approval"
echo ""
echo " 2. Configure your Secrets in Google Secret Manager or Cloud Run env vars:"
echo "    - GEMINI_API_KEY"
echo "    - GITHUB_TOKEN"
echo "    - RESEND_API_KEY"
echo "    - GITHUB_WEBHOOK_SECRET"
echo "    - APPROVAL_RECIPIENT_EMAIL"
echo "    - APPROVAL_FROM_EMAIL"
echo ""
echo " 3. In GitHub Webhook settings, set Payload URL to:"
echo "    ${SERVICE_URL}/webhook"
echo "=================================================================="
