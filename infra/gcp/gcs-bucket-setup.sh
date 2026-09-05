#!/usr/bin/env bash
# Creates the GCS bucket for profile photos: public-read (see
# backend/app/services/storage_service.py — v1 design decision, non-guessable
# UUID object paths instead of ACL-per-object) with CORS enabled so the
# mobile app can PUT directly to a presigned URL from the browser/app.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-northeast3}"
BUCKET_NAME="${GCS_BUCKET_NAME:?Set GCS_BUCKET_NAME, must match backend .env GCS_BUCKET_NAME}"

echo "Creating bucket gs://$BUCKET_NAME in $REGION..."
gcloud storage buckets create "gs://$BUCKET_NAME" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --uniform-bucket-level-access

echo "Applying CORS config..."
gcloud storage buckets update "gs://$BUCKET_NAME" --cors-file="$(dirname "$0")/cors.json"

echo "Granting public read on all objects (profile photos are meant to be seen; non-guessable UUID paths, see storage_service.py)..."
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET_NAME" \
  --member=allUsers --role=roles/storage.objectViewer

echo ""
echo "Done. Set GCS_BUCKET_NAME=$BUCKET_NAME in backend/.env (and the Cloud Run secret, see docs/DEPLOYMENT_GCP.md)."
echo "The backend's service account also needs roles/storage.objectAdmin on this bucket to generate presigned upload URLs — granted in cloudrun-deploy.sh."
