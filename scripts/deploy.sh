#!/bin/bash

# Google Cloud Run Deployment Script
# Usage: ./scripts/deploy.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="synapse-backend"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Starting deployment to Google Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# Step 1: Authenticate with Google Cloud
echo "📝 Checking Google Cloud authentication..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1

# Step 2: Set the project
echo "🔧 Setting project..."
gcloud config set project $PROJECT_ID

# Step 3: Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com

# Step 4: Build the Docker image
echo "🐳 Building Docker image..."
gcloud builds submit --tag $IMAGE_NAME .

# Step 5: Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars GOOGLE_CLOUD_REGION=$REGION \
  --set-env-vars DATABASE="(default)" \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --timeout 300

# Step 6: Get the service URL
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "✅ Deployment successful!"
echo "Service URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/health"

echo ""
echo "🔐 Next steps:"
echo "1. Create secrets in Secret Manager:"
echo "   - service-account-key"
echo "   - google-api-key"
echo "2. Test your deployment: curl $SERVICE_URL/health"
echo "3. Update your frontend to use: $SERVICE_URL"