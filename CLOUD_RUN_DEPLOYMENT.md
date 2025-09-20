# Google Cloud Run Deployment Guide

## Prerequisites

1. **Google Cloud CLI installed**
   ```bash
   # Install gcloud CLI if not already installed
   # https://cloud.google.com/sdk/docs/install
   ```

2. **Docker installed** (for local testing)

3. **Google Cloud Project** with billing enabled

4. **Python 3.13 Compatibility**
   - This deployment uses Python 3.13 to match your local development environment
   - Includes fixes for Pydantic V2 deprecation warnings
   - Compatible with Google protobuf libraries

## Step-by-Step Deployment

### 1. Authentication & Project Setup

#### For PowerShell (Windows):
```powershell
# Login to Google Cloud
gcloud auth login

# Set your project ID (replace with your actual project)
$PROJECT_ID = "calcium-ratio-472014-r9"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com
```

#### For Bash (Linux/Mac):
```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID (replace with your actual project)
export PROJECT_ID="calcium-ratio-472014-r9"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 2. Create Service Account (for Firestore access)

#### For PowerShell (Windows):
```powershell
# Create service account
gcloud iam service-accounts create synapse-backend --display-name="Synapse Backend Service Account"

# Get the service account email
$SA_EMAIL = (gcloud iam service-accounts list --filter="displayName:Synapse Backend Service Account" --format="value(email)")

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/datastore.user"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/firebase.admin"

# Create and download service account key
gcloud iam service-accounts keys create service-account-key.json --iam-account=$SA_EMAIL
```

#### For Bash (Linux/Mac):
```bash
# Create service account
gcloud iam service-accounts create synapse-backend \
    --display-name="Synapse Backend Service Account"

# Get the service account email
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter="displayName:Synapse Backend Service Account" \
    --format="value(email)")

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/firebase.admin"

# Create and download service account key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=$SA_EMAIL
```

### 3. Create Secrets in Secret Manager

```bash
# Create secret for service account key
gcloud secrets create service-account-key \
    --data-file=service-account-key.json

# Create secret for Google API key (replace YOUR_GOOGLE_API_KEY)
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key \
    --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding service-account-key \
    --member="allUsers" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-api-key \
    --member="allUsers" \
    --role="roles/secretmanager.secretAccessor"

# Clean up local key file
rm service-account-key.json
```

### 4. Initialize Firestore Database

```bash
# Create Firestore database (if not already created)
gcloud firestore databases create --region=us-central1

# Upload Firestore indexes
gcloud firestore indexes composite create --collection-group=itineraries \
    --field-config=field-path=sessionId,order=ASCENDING \
    --field-config=field-path=createdAt,order=DESCENDING
```

### 5. Deploy Application

#### Option A: Using PowerShell Script (Windows)
```powershell
.\scripts\deploy.ps1 -ProjectId "your-project-id" -Region "us-central1"
```

#### Option B: Using Bash Script (Linux/Mac)
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh your-project-id us-central1
```

#### Option C: Manual Deployment
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/synapse-backend

gcloud run deploy synapse-backend \
    --image gcr.io/$PROJECT_ID/synapse-backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --set-env-vars GOOGLE_CLOUD_REGION=us-central1 \
    --set-env-vars DATABASE="(default)" \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300
```

### 6. Test Deployment

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe synapse-backend \
    --region=us-central1 --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Test session creation
curl -X POST $SERVICE_URL/session

# Test plantrip endpoint (with sample data)
curl -X POST $SERVICE_URL/plantrip \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Paris, France",
    "budget": 2000,
    "days": 5,
    "sessionId": "test-session"
  }'
```

## Environment Variables

The following environment variables are automatically set by Cloud Run:

- `K_SERVICE`: Indicates running on Cloud Run
- `GOOGLE_CLOUD_PROJECT`: Your project ID
- `GOOGLE_CLOUD_REGION`: Deployment region
- `PORT`: Port number (8080)

## Secret Management

Secrets are accessed via Google Secret Manager:
- `service-account-key`: Firestore service account credentials
- `google-api-key`: Google API key for LLM services

## Troubleshooting

### Common Issues:

1. **Authentication Errors**
   ```bash
   # Re-authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Permission Errors**
   ```bash
   # Check service account permissions
   gcloud projects get-iam-policy $PROJECT_ID
   ```

3. **Firestore Errors**
   ```bash
   # Verify Firestore is enabled
   gcloud firestore databases list
   ```

4. **Build Errors**
   ```bash
   # Check build logs
   gcloud builds list --limit=5
   ```

### View Logs
```bash
# View Cloud Run logs
gcloud logs read --service=synapse-backend --limit=50
```

### Update Deployment
```bash
# Redeploy after changes
gcloud builds submit --tag gcr.io/$PROJECT_ID/synapse-backend
gcloud run services update synapse-backend \
    --image gcr.io/$PROJECT_ID/synapse-backend \
    --region us-central1
```

## Cost Optimization

- **CPU allocation**: Set to 1 CPU for normal loads
- **Memory**: 1GB should be sufficient for most workloads  
- **Max instances**: Limited to 10 to control costs
- **Request timeout**: 300 seconds for LLM processing

## Security Considerations

- Service runs as `allUsers` for public API access
- Secrets are managed through Secret Manager
- Service account has minimal required permissions
- Firestore security rules should be configured separately

## Next Steps

1. Configure custom domain (optional)
2. Set up monitoring and alerting
3. Configure Firestore security rules
4. Set up CI/CD pipeline for automated deployments
5. Configure load balancing for high availability