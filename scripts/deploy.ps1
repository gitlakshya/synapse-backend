# Google Cloud Run Deployment Script (PowerShell)
# Usage: .\scripts\deploy.ps1 -ProjectId "your-project-id" -Region "us-central1"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1"
)

$ServiceName = "synapse-backend"
$ImageName = "gcr.io/$ProjectId/$ServiceName"

Write-Host "🚀 Starting deployment to Google Cloud Run..." -ForegroundColor Green
Write-Host "Project ID: $ProjectId" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Service Name: $ServiceName" -ForegroundColor Cyan

try {
    # Step 1: Check authentication
    Write-Host "📝 Checking Google Cloud authentication..." -ForegroundColor Yellow
    $activeAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" | Select-Object -First 1
    Write-Host "Active account: $activeAccount" -ForegroundColor Green

    # Step 2: Set the project
    Write-Host "🔧 Setting project..." -ForegroundColor Yellow
    gcloud config set project $ProjectId
    
    # Step 3: Enable required APIs
    Write-Host "🔌 Enabling required APIs..." -ForegroundColor Yellow
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable secretmanager.googleapis.com
    gcloud services enable firestore.googleapis.com
    
    # Step 4: Build the Docker image
    Write-Host "🐳 Building Docker image..." -ForegroundColor Yellow
    gcloud builds submit --tag $ImageName .
    
    # Step 5: Deploy to Cloud Run
    Write-Host "☁️ Deploying to Cloud Run..." -ForegroundColor Yellow
    gcloud run deploy $ServiceName `
        --image $ImageName `
        --platform managed `
        --region $Region `
        --allow-unauthenticated `
        --set-env-vars GOOGLE_CLOUD_PROJECT=$ProjectId `
        --set-env-vars GOOGLE_CLOUD_REGION=$Region `
        --set-env-vars DATABASE="(default)" `
        --memory 1Gi `
        --cpu 1 `
        --max-instances 10 `
        --timeout 300
    
    # Step 6: Get the service URL
    Write-Host "🌐 Getting service URL..." -ForegroundColor Yellow
    $ServiceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"
    
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "Service URL: $ServiceUrl" -ForegroundColor Cyan
    Write-Host "Health check: $ServiceUrl/health" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "🔐 Next steps:" -ForegroundColor Yellow
    Write-Host "1. Create secrets in Secret Manager:" -ForegroundColor White
    Write-Host "   - service-account-key" -ForegroundColor Gray
    Write-Host "   - google-api-key" -ForegroundColor Gray
    Write-Host "2. Test your deployment: curl $ServiceUrl/health" -ForegroundColor White
    Write-Host "3. Update your frontend to use: $ServiceUrl" -ForegroundColor White

} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}