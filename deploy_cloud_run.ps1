# ==============================================================================
# PowerShell Google Cloud Run Deployment Script for AI Code Review Agent
# ==============================================================================
[CmdletBinding()]
param (
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$ServiceName = "ai-code-review-agent",
    [string]$Region = "us-central1",
    [string]$StorageBackend = "json"
)

if (-not $ProjectId -or $ProjectId -eq "your-gcp-project-id") {
    Write-Error "Please specify a valid -ProjectId or set the GCP_PROJECT_ID environment variable."
    exit 1
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Deploying AI Code Review Agent to Google Cloud Run" -ForegroundColor Cyan
Write-Host " Project:  $ProjectId"
Write-Host " Service:  $ServiceName"
Write-Host " Region:   $Region"
Write-Host "=================================================================="

gcloud config set project $ProjectId

# Deploy from current source directory
# IMPORTANT:
#  --no-cpu-throttling keeps background tasks alive after returning HTTP 202
gcloud run deploy $ServiceName `
  --source . `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --no-cpu-throttling `
  --port 8080 `
  --memory 1Gi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 10 `
  --set-env-vars "STORAGE_BACKEND=$StorageBackend"

$ServiceUrl = gcloud run services describe $ServiceName --platform managed --region $Region --format 'value(status.url)'

Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host " Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host ""
Write-Host " Next Steps:"
Write-Host " 1. Update APPROVAL_BASE_URL:"
Write-Host "    gcloud run services update $ServiceName --region $Region --update-env-vars APPROVAL_BASE_URL=$ServiceUrl/approval"
Write-Host ""
Write-Host " 2. Set your API keys and secrets:"
Write-Host "    - GEMINI_API_KEY"
Write-Host "    - GITHUB_TOKEN"
Write-Host "    - RESEND_API_KEY"
Write-Host "    - GITHUB_WEBHOOK_SECRET"
Write-Host "    - APPROVAL_RECIPIENT_EMAIL"
Write-Host "    - APPROVAL_FROM_EMAIL"
Write-Host ""
Write-Host " 3. In GitHub Webhook settings, set Payload URL to:"
Write-Host "    $ServiceUrl/webhook"
Write-Host "=================================================================="
