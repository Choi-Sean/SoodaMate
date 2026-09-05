#!/usr/bin/env bash
# Builds the backend image from source (Cloud Build, using backend/Dockerfile)
# and deploys it to Cloud Run, wired to Cloud SQL + Secret Manager secrets
# created by cloudsql-setup.sh / the manual secret-creation steps in
# docs/DEPLOYMENT_GCP.md. Re-run any time to deploy a new revision.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="${CLOUDRUN_SERVICE_NAME:-suda-date-backend}"
SA_NAME="${CLOUDRUN_SA_NAME:-suda-date-backend-sa}"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
CLOUDSQL_INSTANCE_NAME="${CLOUDSQL_INSTANCE_NAME:-suda-date-db}"
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:?Set GCS_BUCKET_NAME}"

CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe "$CLOUDSQL_INSTANCE_NAME" \
  --project="$PROJECT_ID" --format='value(connectionName)')

echo "Ensuring service account $SA_EMAIL exists with the roles the backend needs..."
gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT_ID" \
  --display-name="SuDa Date backend (Cloud Run)" 2>/dev/null || true

for role in roles/cloudsql.client roles/storage.objectAdmin roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" --role="$role" --quiet >/dev/null
done

echo "Deploying $SERVICE_NAME to Cloud Run in $REGION..."
gcloud run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --source="$(dirname "$0")/../../backend" \
  --service-account="$SA_EMAIL" \
  --add-cloudsql-instances="$CLOUDSQL_CONNECTION_NAME" \
  --set-env-vars="APP_ENV=production,GCS_BUCKET_NAME=$GCS_BUCKET_NAME" \
  --set-secrets="DATABASE_URL=suda-date-database-url:latest,SECRET_KEY=suda-date-secret-key:latest,GOOGLE_OAUTH_CLIENT_ID=suda-date-google-oauth-client-id:latest,KAKAO_REST_API_KEY=suda-date-kakao-rest-api-key:latest" \
  --set-secrets="/secrets/firebase-service-account.json=suda-date-firebase-credentials:latest" \
  --update-env-vars="FIREBASE_CREDENTIALS_PATH=/secrets/firebase-service-account.json" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')
echo ""
echo "Deployed: $SERVICE_URL"
echo "Verify: curl $SERVICE_URL/health"
echo "Point mobile/.env's EXPO_PUBLIC_API_BASE_URL at this URL."
