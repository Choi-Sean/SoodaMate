#!/usr/bin/env bash
# Creates the Cloud SQL for PostgreSQL instance + database + app user used
# by the backend in production. Run once per environment (e.g. once for
# staging, once for prod) after `gcloud auth login` and `gcloud config set
# project <PROJECT_ID>`.
#
# Prerequisite: a GCP project with billing enabled (external — the user
# creates this, see docs/DEPLOYMENT_GCP.md).
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-northeast3}"          # Seoul, closest to the target market
INSTANCE_NAME="${CLOUDSQL_INSTANCE_NAME:-suda-date-db}"
DB_NAME="${CLOUDSQL_DB_NAME:-suda_date}"
DB_USER="${CLOUDSQL_DB_USER:-suda}"

echo "Creating Cloud SQL instance '$INSTANCE_NAME' in $REGION (project $PROJECT_ID)..."
gcloud sql instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --database-version=POSTGRES_16 \
  --region="$REGION" \
  --tier=db-f1-micro \
  --storage-auto-increase

echo "Creating database '$DB_NAME'..."
gcloud sql databases create "$DB_NAME" --instance="$INSTANCE_NAME" --project="$PROJECT_ID"

echo "Creating app user '$DB_USER' (you'll be prompted for a password — save it, it goes into Secret Manager next)..."
gcloud sql users create "$DB_USER" --instance="$INSTANCE_NAME" --project="$PROJECT_ID" --prompt-for-password

CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" --project="$PROJECT_ID" --format='value(connectionName)')
echo ""
echo "Done. Cloud SQL connection name: $CONNECTION_NAME"
echo "Cloud Run's DATABASE_URL (via the Cloud SQL Auth Proxy socket Cloud Run mounts automatically):"
echo "  postgresql+asyncpg://$DB_USER:<password>@/$DB_NAME?host=/cloudsql/$CONNECTION_NAME"
echo "Store that as a Secret Manager secret — see docs/DEPLOYMENT_GCP.md."
